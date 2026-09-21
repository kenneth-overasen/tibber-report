"""Turns raw Tibber consumption nodes into a report.

VAT model
---------
Tibber reports ``unitPrice`` *including* VAT and ``unitPriceVAT`` as the VAT
share already contained in it.  So for every hour:

    unit_price_incl_vat = unitPrice
    unit_price_ex_vat   = unitPrice - unitPriceVAT
    cost_incl_vat       = consumption * unitPrice        (== the API's `cost`)
    vat                 = consumption * unitPriceVAT
    cost_ex_vat         = cost_incl_vat - vat

A fixed price override replaces the unit price only; consumption is untouched.
The override is a plain price per kWh -- VAT does not apply to it, so its cost
is simply consumption x price, with no VAT split.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .i18n import DEFAULT_LOCALE, LocalizedError, warning_text

DEFAULT_VAT_RATE = 0.25


class ReportError(LocalizedError, ValueError):
    """Raised for invalid report parameters. Carries a catalogue key."""


@dataclass
class FixedPrice:
    """A user-supplied price per kWh that overrides the spot price.

    It is a flat contract price: no VAT is added to it and none is split out
    of it.
    """

    price: float


def get_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ReportError("err.unknown_timezone", name=name) from exc


def parse_node_time(value: str) -> datetime:
    """Parse a Tibber timestamp such as '2026-08-13T13:00:00.000+02:00'."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ReportError("err.bad_timestamp", value=value) from exc
    if parsed.tzinfo is None:
        raise ReportError("err.no_offset", value=value)
    return parsed


def parse_local(value: str, zone: ZoneInfo) -> datetime:
    """Parse a 'YYYY-MM-DDTHH:MM' (or with seconds) wall-clock time in `zone`."""
    text = value.strip()
    if text.endswith("Z") or "+" in text[10:]:
        # Already absolute -- honour it as-is.
        return parse_node_time(text)
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=zone)
        except ValueError:
            continue
    raise ReportError("err.bad_local", value=value)


def hours_back_from_now(start: datetime, now: datetime | None = None) -> int:
    """How many hourly nodes to request so that `start` is covered."""
    now = now or datetime.now(tz=start.tzinfo)
    delta = now - start
    if delta.total_seconds() <= 0:
        return 1
    # +2 for a safety margin across DST shifts and partial hours.
    return int(math.ceil(delta.total_seconds() / 3600.0)) + 2


def derive_vat_rate(nodes: list[dict]) -> float | None:
    """Infer the VAT rate actually applied in the period.

    Returns None when the data gives no usable signal (e.g. VAT-exempt
    regions where every unitPriceVAT is 0, or missing prices).
    """
    total_ex = 0.0
    total_vat = 0.0
    for node in nodes:
        unit_price = node.get("unitPrice")
        unit_vat = node.get("unitPriceVAT")
        if unit_price is None or unit_vat is None:
            continue
        total_ex += unit_price - unit_vat
        total_vat += unit_vat
    if total_ex <= 0:
        return None
    return total_vat / total_ex


@dataclass
class HourRow:
    start: datetime
    end: datetime
    consumption: float
    unit_price_incl_vat: float | None
    unit_price_ex_vat: float | None
    unit_price_vat: float | None
    spot_cost_incl_vat: float
    spot_cost_ex_vat: float
    spot_vat: float
    fixed_cost: float | None = None  # consumption x fixed price, no VAT
    estimated: bool = False  # cost computed locally, not returned by the API

    def as_dict(self, fixed_only: bool = False) -> dict:
        row = {
            "from": self.start.isoformat(),
            "to": self.end.isoformat(),
            "consumption": self.consumption,
        }
        if not fixed_only:
            row.update(
                {
                    "unitPriceInclVat": self.unit_price_incl_vat,
                    "unitPriceExVat": self.unit_price_ex_vat,
                    "unitPriceVat": self.unit_price_vat,
                    "spotCostInclVat": self.spot_cost_incl_vat,
                    "spotCostExVat": self.spot_cost_ex_vat,
                    "spotVat": self.spot_vat,
                    "estimated": self.estimated,
                }
            )
        if self.fixed_cost is not None:
            row["fixedCost"] = self.fixed_cost
        return row


@dataclass
class Report:
    home: dict
    start: datetime
    end: datetime
    currency: str
    rows: list[HourRow]
    vat_rate: float
    vat_rate_derived: bool
    fixed_price: float | None = None  # per kWh, VAT does not apply
    # Report the fixed price on its own, leaving the spot comparison out.
    fixed_only: bool = False
    warnings: list[tuple[str, dict]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    # -- totals -----------------------------------------------------------
    @property
    def total_consumption(self) -> float:
        return sum(r.consumption for r in self.rows)

    @property
    def total_spot_incl_vat(self) -> float:
        return sum(r.spot_cost_incl_vat for r in self.rows)

    @property
    def total_spot_ex_vat(self) -> float:
        return sum(r.spot_cost_ex_vat for r in self.rows)

    @property
    def total_spot_vat(self) -> float:
        return sum(r.spot_vat for r in self.rows)

    @property
    def total_fixed(self) -> float | None:
        if self.fixed_price is None:
            return None
        return sum(r.fixed_cost or 0.0 for r in self.rows)

    @property
    def average_spot_price_incl_vat(self) -> float | None:
        """Consumption-weighted average price per kWh."""
        if self.total_consumption <= 0:
            return None
        return self.total_spot_incl_vat / self.total_consumption

    @property
    def peak_row(self) -> HourRow | None:
        rows = [r for r in self.rows if r.consumption > 0]
        return max(rows, key=lambda r: r.consumption) if rows else None

    @property
    def difference(self) -> float | None:
        """Fixed minus spot incl. VAT -- what each contract actually costs.

        Positive means the fixed price costs more.
        """
        total_fixed = self.total_fixed
        if total_fixed is None:
            return None
        return total_fixed - self.total_spot_incl_vat

    def rendered_warnings(self, locale: str | None = DEFAULT_LOCALE) -> list[str]:
        return [warning_text(locale, code, params) for code, params in self.warnings]

    def label(self) -> str:
        postal = self.home.get("postalCode") or "home"
        return (
            f"tibber_{postal}_{self.start:%Y%m%d%H%M}_{self.end:%Y%m%d%H%M}"
        )

    def as_dict(self, locale: str | None = DEFAULT_LOCALE) -> dict:
        """The report as JSON-ready data.

        In `fixed_only` mode the spot side is left out entirely -- including
        the VAT rate, which describes the spot price and not the fixed one.
        """
        summary: dict = {"totalConsumption": self.total_consumption}
        if not self.fixed_only:
            summary["spot"] = {
                "inclVat": self.total_spot_incl_vat,
                "exVat": self.total_spot_ex_vat,
                "vat": self.total_spot_vat,
            }
        if self.fixed_price is not None:
            summary["fixed"] = {"total": self.total_fixed}
        if not self.fixed_only:
            summary["difference"] = self.difference
            summary["averageSpotPriceInclVat"] = self.average_spot_price_incl_vat
        summary["peakHour"] = (
            None
            if self.peak_row is None
            else {
                "from": self.peak_row.start.isoformat(),
                "consumption": self.peak_row.consumption,
            }
        )

        payload = {
            "home": self.home,
            "period": {
                "from": self.start.isoformat(),
                "to": self.end.isoformat(),
                "hours": len(self.rows),
            },
            "currency": self.currency,
            "fixedOnly": self.fixed_only,
            "fixedPrice": self.fixed_price,
            "summary": summary,
            "hours": [r.as_dict(self.fixed_only) for r in self.rows],
            "warnings": self.rendered_warnings(locale),
            "warningCodes": [code for code, _ in self.warnings],
            "generatedAt": self.generated_at.isoformat(),
            "label": self.label(),
        }
        if not self.fixed_only:
            payload["vatRate"] = self.vat_rate
            payload["vatRateDerived"] = self.vat_rate_derived
        return payload


def build_report(
    *,
    home: dict,
    nodes: list[dict],
    start: datetime,
    end: datetime,
    zone: ZoneInfo,
    fixed_price: FixedPrice | None = None,
    fixed_only: bool = False,
    currency_fallback: str = "NOK",
) -> Report:
    """Filter `nodes` to [start, end) and compute per-hour and total figures.

    `fixed_only` reports the fixed price on its own and drops the spot
    comparison; it needs a `fixed_price` to mean anything, and is ignored
    without one.
    """
    if end <= start:
        raise ReportError("err.end_before_start")

    derived = derive_vat_rate(nodes)
    vat_rate = derived if derived is not None else DEFAULT_VAT_RATE
    vat_rate_derived = derived is not None

    fixed_unit_price = fixed_price.price if fixed_price is not None else None
    fixed_only = fixed_only and fixed_unit_price is not None

    warnings: list[tuple[str, dict]] = []
    currency = currency_fallback
    rows: list[HourRow] = []
    missing_price_hours = 0
    earliest_seen: datetime | None = None

    for node in nodes:
        node_start = parse_node_time(node["from"]).astimezone(zone)
        node_end = parse_node_time(node["to"]).astimezone(zone)

        if earliest_seen is None or node_start < earliest_seen:
            earliest_seen = node_start

        # Half-open interval: an hour belongs to the period if it starts
        # inside it and does not run past the end.
        if node_start < start or node_end > end:
            continue

        if node.get("currency"):
            currency = node["currency"]

        consumption = node.get("consumption") or 0.0
        unit_price = node.get("unitPrice")
        unit_vat = node.get("unitPriceVAT")

        if unit_price is None:
            missing_price_hours += 1
            unit_price_ex = unit_vat_value = None
            spot_incl = spot_vat_amount = spot_ex = 0.0
            estimated = False
        else:
            unit_vat = unit_vat or 0.0
            unit_price_ex = unit_price - unit_vat
            unit_vat_value = unit_vat
            api_cost = node.get("cost")
            estimated = api_cost is None
            spot_incl = api_cost if api_cost is not None else consumption * unit_price
            spot_vat_amount = consumption * unit_vat
            spot_ex = spot_incl - spot_vat_amount

        row = HourRow(
            start=node_start,
            end=node_end,
            consumption=consumption,
            unit_price_incl_vat=unit_price,
            unit_price_ex_vat=unit_price_ex,
            unit_price_vat=unit_vat_value,
            spot_cost_incl_vat=spot_incl,
            spot_cost_ex_vat=spot_ex,
            spot_vat=spot_vat_amount,
            estimated=estimated,
        )

        if fixed_unit_price is not None:
            row.fixed_cost = consumption * fixed_unit_price

        rows.append(row)

    rows.sort(key=lambda r: r.start)

    if not rows:
        warnings.append(("warn.no_data", {}))
    else:
        expected = int(round((end - start).total_seconds() / 3600.0))
        if len(rows) < expected:
            warnings.append(
                (
                    "warn.partial_hours",
                    {"missing": expected - len(rows), "expected": expected},
                )
            )
        if earliest_seen is not None and earliest_seen > start and len(rows) < expected:
            warnings.append(
                (
                    "warn.earliest",
                    {"timestamp": f"{earliest_seen:%Y-%m-%d %H:%M}"},
                )
            )

    # Both of these describe the spot side only: a fixed cost needs nothing
    # from the API but the consumption, so neither is worth raising when the
    # spot price is not reported.
    if missing_price_hours and not fixed_only:
        warnings.append(("warn.missing_price", {"count": missing_price_hours}))
    if rows and not vat_rate_derived and not fixed_only:
        warnings.append(("warn.vat_assumed", {"rate": DEFAULT_VAT_RATE}))

    return Report(
        home=home,
        start=start,
        end=end,
        currency=currency,
        rows=rows,
        vat_rate=vat_rate,
        vat_rate_derived=vat_rate_derived,
        fixed_price=fixed_unit_price,
        fixed_only=fixed_only,
        warnings=warnings,
    )
