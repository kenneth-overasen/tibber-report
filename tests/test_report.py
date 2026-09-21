"""Unit tests for the report arithmetic. Run with: python -m pytest tests"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.report import (  # noqa: E402
    FixedPrice,
    ReportError,
    build_report,
    derive_vat_rate,
    hours_back_from_now,
    parse_local,
    parse_node_time,
)

OSLO = ZoneInfo("Europe/Oslo")
HOME = {"postalCode": "1747", "city": "Skjeberg", "timeZone": "Europe/Oslo"}


def node(hour: int, consumption: float, unit_price: float, vat: float, cost=None):
    """One hourly node, mirroring Tibber's shape (unitPrice includes VAT)."""
    return {
        "from": f"2026-08-13T{hour:02d}:00:00.000+02:00",
        "to": f"2026-08-13T{hour + 1:02d}:00:00.000+02:00",
        "consumption": consumption,
        "unitPrice": unit_price,
        "unitPriceVAT": vat,
        "consumptionUnit": "kWh",
        "cost": consumption * unit_price if cost is None else cost,
        "currency": "NOK",
    }


def make(nodes, start_hour=13, end_hour=16, fixed=None):
    return build_report(
        home=HOME,
        nodes=nodes,
        start=datetime(2026, 8, 13, start_hour, tzinfo=OSLO),
        end=datetime(2026, 8, 13, end_hour, tzinfo=OSLO),
        zone=OSLO,
        fixed_price=fixed,
    )


# ------------------------------------------------------------ parsing -----
def test_parse_node_time_handles_offset_and_z():
    assert parse_node_time("2026-08-13T13:00:00.000+02:00").hour == 13
    assert parse_node_time("2026-08-13T11:00:00Z").utcoffset().total_seconds() == 0


def test_parse_local_accepts_date_and_datetime():
    assert parse_local("2026-08-13", OSLO) == datetime(2026, 8, 13, tzinfo=OSLO)
    assert parse_local("2026-08-13T07:30", OSLO).minute == 30


def test_parse_local_rejects_nonsense():
    with pytest.raises(ReportError):
        parse_local("13.08.2026", OSLO)


def test_hours_back_from_now_covers_the_start():
    start = datetime(2026, 8, 13, 12, tzinfo=OSLO)
    now = datetime(2026, 8, 14, 12, tzinfo=OSLO)
    assert hours_back_from_now(start, now) == 26  # 24 hours + 2 margin


# --------------------------------------------------------------- VAT ------
def test_derive_vat_rate_from_unit_prices():
    nodes = [node(13, 1.0, 1.25, 0.25), node(14, 1.0, 2.50, 0.50)]
    assert derive_vat_rate(nodes) == pytest.approx(0.25)


def test_derive_vat_rate_returns_none_for_vat_exempt_region():
    nodes = [node(13, 1.0, 1.00, 0.0)]
    assert derive_vat_rate(nodes) == pytest.approx(0.0)


def test_vat_is_not_added_on_top_of_cost():
    """Tibber's `cost` already includes VAT; the totals must not double it."""
    report = make([node(13, 2.0, 1.25, 0.25)])
    assert report.total_spot_incl_vat == pytest.approx(2.5)
    assert report.total_spot_vat == pytest.approx(0.5)
    assert report.total_spot_ex_vat == pytest.approx(2.0)


# ------------------------------------------------------------ filtering ---
def test_hours_outside_the_period_are_excluded():
    nodes = [node(h, 1.0, 1.25, 0.25) for h in range(10, 20)]
    report = make(nodes, start_hour=13, end_hour=16)
    assert [r.start.hour for r in report.rows] == [13, 14, 15]
    assert report.total_consumption == pytest.approx(3.0)


def test_missing_consumption_and_cost_are_treated_as_zero():
    n = node(13, 0, 1.25, 0.25)
    n["consumption"] = None
    n["cost"] = None
    report = make([n])
    assert report.total_consumption == 0
    assert report.total_spot_incl_vat == 0


def test_partial_data_produces_a_warning():
    report = make([node(13, 1.0, 1.25, 0.25)], start_hour=13, end_hour=16)
    codes = [code for code, _ in report.warnings]
    assert "warn.partial_hours" in codes
    params = dict(report.warnings)["warn.partial_hours"]
    assert params == {"missing": 2, "expected": 3}


def test_end_before_start_is_rejected():
    with pytest.raises(ReportError):
        make([], start_hour=16, end_hour=13)


# --------------------------------------------------------- fixed price ----
def test_fixed_cost_is_consumption_times_the_price():
    """No VAT is added to, or split out of, a fixed price."""
    nodes = [node(13, 10.0, 1.25, 0.25)]
    report = make(nodes, fixed=FixedPrice(price=2.00))
    assert report.fixed_price == pytest.approx(2.00)
    assert report.total_fixed == pytest.approx(20.0)
    assert report.rows[0].fixed_cost == pytest.approx(20.0)


def test_fixed_price_is_untouched_by_the_spot_vat_rate():
    """The rate derived from the API data applies to the spot price only."""
    nodes = [node(13, 10.0, 1.25, 0.25)]  # data says 25 %
    report = make(nodes, fixed=FixedPrice(price=1.00))
    assert report.vat_rate == pytest.approx(0.25)
    assert report.vat_rate_derived is True
    assert report.total_spot_vat == pytest.approx(2.5)
    assert report.total_fixed == pytest.approx(10.0)


def test_difference_compares_fixed_against_spot_incl_vat():
    nodes = [node(13, 10.0, 1.25, 0.25)]  # spot total 12.50 incl. VAT
    report = make(nodes, fixed=FixedPrice(price=2.00))
    assert report.difference == pytest.approx(7.5)


# -------------------------------------------------------------- output ----
def test_average_price_is_consumption_weighted():
    nodes = [node(13, 1.0, 1.00, 0.20), node(14, 3.0, 2.00, 0.40)]
    report = make(nodes)
    # (1*1.00 + 3*2.00) / 4 = 1.75
    assert report.average_spot_price_incl_vat == pytest.approx(1.75)


def test_report_dict_and_exports_round_trip():
    from app.exporters import to_csv, to_pdf

    nodes = [node(h, 1.5, 1.25, 0.25) for h in (13, 14, 15)]
    report = make(nodes, fixed=FixedPrice(price=1.10))

    payload = report.as_dict()
    assert payload["summary"]["totalConsumption"] == pytest.approx(4.5)
    assert payload["fixedPrice"] == pytest.approx(1.10)
    assert payload["summary"]["fixed"] == {"total": pytest.approx(4.95)}
    assert len(payload["hours"]) == 3
    assert payload["label"] == "tibber_1747_202608131300_202608131600"

    csv_text = to_csv(report)
    assert "Hourly detail" in csv_text
    assert "TOTAL" in csv_text

    pdf_bytes = to_pdf(report)
    assert pdf_bytes.startswith(b"%PDF")


def test_vat_is_assumed_when_it_cannot_be_derived():
    n = node(13, 1.0, 1.25, 0.25)
    n["unitPrice"] = None  # nothing to derive from
    n["unitPriceVAT"] = None
    report = make([n], fixed=FixedPrice(price=1.0))
    assert "warn.vat_assumed" in [code for code, _ in report.warnings]
    assert report.vat_rate_derived is False
