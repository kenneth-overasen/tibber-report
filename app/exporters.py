"""Download formats for a Report: CSV and a printable PDF receipt.

Both formats are produced in the caller's locale: labels come from the
translation catalogue and numbers use that locale's decimal mark.
"""
from __future__ import annotations

import csv
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .i18n import DEFAULT_LOCALE, format_number, format_percent
from .i18n import t as _t
from .report import Report

ACCENT = colors.HexColor("#0f6f5c")
INK = colors.HexColor("#1b2430")
MUTED = colors.HexColor("#6b7785")
RULE = colors.HexColor("#d9dee5")
ZEBRA = colors.HexColor("#f4f6f8")


class Loc:
    """Locale-bound label lookup and number formatting."""

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self.locale = locale

    def t(self, key: str, **params) -> str:
        return _t(self.locale, key, **params)

    def n(self, value: float | None, digits: int = 2) -> str:
        return format_number(value, digits, self.locale)

    def pct(self, value: float, digits: int = 1) -> str:
        return format_percent(value, self.locale, digits)


def home_label(report: Report, locale: str = DEFAULT_LOCALE) -> str:
    home = report.home
    parts = [home.get("address1"), home.get("postalCode"), home.get("city")]
    address = " ".join(p for p in parts if p)
    nickname = home.get("nickname")
    if nickname and address:
        return f"{nickname} - {address}"
    return nickname or address or _t(locale, "rep.unknown_address")


def _fixed_price_detail(report: Report, L: Loc) -> str:
    """'1,2500 NOK/kWh incl. VAT (1,0000 excl. VAT)' in the right language."""
    extra = ""
    if (
        report.fixed_vat_rate is not None
        and abs(report.fixed_vat_rate - report.vat_rate) > 1e-9
    ):
        extra = L.t("rep.fixed_vat_extra", rate=L.pct(report.fixed_vat_rate))
    return L.t(
        "rep.fixed_detail",
        incl=L.n(report.fixed_price_incl_vat, 4),
        excl=L.n(report.fixed_price_ex_vat, 4),
        currency=report.currency,
        extra=extra,
    )


# ---------------------------------------------------------------- CSV -----
def to_csv(report: Report, locale: str = DEFAULT_LOCALE) -> str:
    L = Loc(locale)
    buffer = io.StringIO()
    # Semicolon-separated: the Norwegian decimal mark is a comma, and Excel in
    # a Norwegian locale expects ';' anyway.
    writer = csv.writer(buffer, delimiter=";")
    cur = report.currency
    has_fixed = report.fixed_price_incl_vat is not None

    writer.writerow([L.t("rep.csv_title")])
    writer.writerow([L.t("rep.home"), home_label(report, locale)])
    writer.writerow([L.t("rep.period_from"), report.start.strftime("%Y-%m-%d %H:%M %Z")])
    writer.writerow([L.t("rep.period_to"), report.end.strftime("%Y-%m-%d %H:%M %Z")])
    writer.writerow(
        [L.t("rep.generated"), report.generated_at.strftime("%Y-%m-%d %H:%M %Z")]
    )
    writer.writerow([L.t("rep.currency"), cur])
    writer.writerow(
        [
            L.t("rep.vat_rate"),
            L.pct(report.vat_rate),
            L.t("rep.derived") if report.vat_rate_derived else L.t("rep.assumed"),
        ]
    )
    if has_fixed:
        writer.writerow([L.t("rep.fixed_override"), _fixed_price_detail(report, L)])
    writer.writerow([])

    writer.writerow([L.t("rep.summary")])
    writer.writerow([L.t("rep.hours_with_data"), len(report.rows)])
    writer.writerow([L.t("rep.total_consumption"), L.n(report.total_consumption, 3)])
    writer.writerow(
        [L.t("rep.spot_total_incl", currency=cur), L.n(report.total_spot_incl_vat)]
    )
    writer.writerow(
        [L.t("rep.spot_total_excl", currency=cur), L.n(report.total_spot_ex_vat)]
    )
    writer.writerow([L.t("rep.spot_vat", currency=cur), L.n(report.total_spot_vat)])
    writer.writerow(
        [
            L.t("rep.avg_price", currency=cur),
            L.n(report.average_spot_price_incl_vat, 4),
        ]
    )
    if has_fixed:
        writer.writerow(
            [L.t("rep.fixed_total_incl", currency=cur), L.n(report.total_fixed_incl_vat)]
        )
        writer.writerow(
            [L.t("rep.fixed_total_excl", currency=cur), L.n(report.total_fixed_ex_vat)]
        )
        writer.writerow(
            [L.t("rep.fixed_vat", currency=cur), L.n(report.total_fixed_vat)]
        )
        writer.writerow(
            [L.t("rep.difference", currency=cur), L.n(report.difference_incl_vat)]
        )
    writer.writerow([])

    header = [
        L.t("rep.from_col"),
        L.t("rep.to_col"),
        f"{L.t('rep.consumption')} (kWh)",
        L.t("rep.unit_price_incl", currency=cur),
        L.t("rep.unit_price_excl", currency=cur),
        L.t("rep.spot_cost_incl", currency=cur),
        L.t("rep.spot_cost_excl", currency=cur),
        L.t("rep.spot_cost_vat", currency=cur),
    ]
    if has_fixed:
        header += [
            L.t("rep.fixed_cost_incl", currency=cur),
            L.t("rep.fixed_cost_excl", currency=cur),
            L.t("rep.fixed_cost_vat", currency=cur),
        ]
    writer.writerow([L.t("rep.hourly_detail")])
    writer.writerow(header)

    for row in report.rows:
        line = [
            row.start.strftime("%Y-%m-%d %H:%M"),
            row.end.strftime("%Y-%m-%d %H:%M"),
            L.n(row.consumption, 3),
            L.n(row.unit_price_incl_vat, 4),
            L.n(row.unit_price_ex_vat, 4),
            L.n(row.spot_cost_incl_vat),
            L.n(row.spot_cost_ex_vat),
            L.n(row.spot_vat),
        ]
        if has_fixed:
            line += [
                L.n(row.fixed_cost_incl_vat),
                L.n(row.fixed_cost_ex_vat),
                L.n(row.fixed_vat),
            ]
        writer.writerow(line)

    total_line = [
        L.t("rep.total"),
        "",
        L.n(report.total_consumption, 3),
        "",
        "",
        L.n(report.total_spot_incl_vat),
        L.n(report.total_spot_ex_vat),
        L.n(report.total_spot_vat),
    ]
    if has_fixed:
        total_line += [
            L.n(report.total_fixed_incl_vat),
            L.n(report.total_fixed_ex_vat),
            L.n(report.total_fixed_vat),
        ]
    writer.writerow(total_line)

    for warning in report.rendered_warnings(locale):
        writer.writerow([])
        writer.writerow([L.t("rep.note"), warning])

    return buffer.getvalue()


# ---------------------------------------------------------------- PDF -----
def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"], fontSize=19, leading=23,
            textColor=INK, alignment=0, spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "sub", parent=base["Normal"], fontSize=9.5, leading=13, textColor=MUTED,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=11.5, leading=14,
            textColor=ACCENT, spaceBefore=4, spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "cell", parent=base["Normal"], fontSize=8, leading=10, textColor=INK,
        ),
        "note": ParagraphStyle(
            "note", parent=base["Normal"], fontSize=8, leading=11, textColor=MUTED,
        ),
        "right": ParagraphStyle(
            "right", parent=base["Normal"], fontSize=9, leading=12,
            textColor=INK, alignment=TA_RIGHT,
        ),
    }


def _meta_table(report: Report, st: dict, L: Loc) -> Table:
    vat_note = L.t("rep.derived") if report.vat_rate_derived else L.t("rep.assumed")
    rows = [
        [L.t("rep.home"), home_label(report, L.locale)],
        [
            L.t("rep.period"),
            f"{report.start:%Y-%m-%d %H:%M} {L.t('rep.to')} "
            f"{report.end:%Y-%m-%d %H:%M} ({report.start.tzname() or ''})",
        ],
        [L.t("rep.hours_with_data"), str(len(report.rows))],
        [L.t("rep.currency"), report.currency],
        [L.t("rep.vat_rate"), f"{L.pct(report.vat_rate)} ({vat_note})"],
    ]
    if report.fixed_price_incl_vat is not None:
        rows.append([L.t("rep.fixed_override"), _fixed_price_detail(report, L)])
    rows.append(
        [L.t("rep.generated"), report.generated_at.strftime("%Y-%m-%d %H:%M %Z")]
    )

    table = Table(
        [[Paragraph(f"<b>{k}</b>", st["cell"]), Paragraph(str(v), st["cell"])]
         for k, v in rows],
        colWidths=[42 * mm, 136 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return table


def _summary_table(report: Report, st: dict, L: Loc) -> Table:
    cur = report.currency
    has_fixed = report.fixed_price_incl_vat is not None

    head = ["", L.t("rep.spot_currency", currency=cur)]
    if has_fixed:
        head.append(L.t("rep.fixed_currency", currency=cur))
    data = [head]

    # Label the VAT row with a rate only when spot and fixed agree on it.
    same_rate = (
        not has_fixed
        or report.fixed_vat_rate is None
        or abs(report.fixed_vat_rate - report.vat_rate) < 1e-9
    )
    vat_label = (
        f"{L.t('rep.vat')} ({L.pct(report.vat_rate)})" if same_rate else L.t("rep.vat")
    )

    def line(label: str, spot, fixed):
        row = [label, L.n(spot)]
        if has_fixed:
            row.append(L.n(fixed))
        return row

    data.append(
        line(L.t("rep.excl_vat"), report.total_spot_ex_vat, report.total_fixed_ex_vat)
    )
    data.append(line(vat_label, report.total_spot_vat, report.total_fixed_vat))
    data.append(
        line(
            L.t("rep.total_incl_vat"),
            report.total_spot_incl_vat,
            report.total_fixed_incl_vat,
        )
    )

    widths = [60 * mm, 40 * mm] + ([40 * mm] if has_fixed else [])
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
                ("TEXTCOLOR", (0, -1), (-1, -1), ACCENT),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE),
                ("LINEABOVE", (0, -1), (-1, -1), 0.8, RULE),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
            ]
        )
    )
    return table


def _headline_table(report: Report, st: dict, L: Loc) -> Table:
    cur = report.currency
    avg = report.average_spot_price_incl_vat
    tiles = [
        (L.t("rep.consumption"), f"{L.n(report.total_consumption, 2)} kWh"),
        (L.t("rep.spot_tile"), f"{L.n(report.total_spot_incl_vat)} {cur}"),
    ]
    if report.fixed_price_incl_vat is not None:
        diff = report.difference_incl_vat or 0.0
        sign = "+" if diff >= 0 else "-"
        tiles.append(
            (L.t("rep.fixed_tile"), f"{L.n(report.total_fixed_incl_vat)} {cur}")
        )
        tiles.append(
            (L.t("rep.difference_tile"), f"{sign}{L.n(abs(diff))} {cur}")
        )
    else:
        tiles.append(
            (
                L.t("rep.avg_tile"),
                f"{L.n(avg, 4)} {cur}/kWh" if avg is not None else "-",
            )
        )

    width = (178 / len(tiles)) * mm
    header = [
        Paragraph(f'<font color="#6b7785" size="7">{label.upper()}</font>', st["cell"])
        for label, _ in tiles
    ]
    values = [
        Paragraph(f'<font color="#1b2430" size="13"><b>{value}</b></font>', st["cell"])
        for _, value in tiles
    ]
    table = Table([header, values], colWidths=[width] * len(tiles))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), ZEBRA),
                ("BOX", (0, 0), (-1, -1), 0.5, RULE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("TOPPADDING", (0, 0), (-1, 0), 7),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
                ("TOPPADDING", (0, 1), (-1, 1), 0),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _detail_table(report: Report, st: dict, L: Loc) -> Table:
    cur = report.currency
    has_fixed = report.fixed_price_incl_vat is not None

    header = [
        L.t("rep.hour"),
        L.t("rep.kwh"),
        L.t("rep.unit_price_short", currency=cur),
        L.t("rep.excl_vat"),
        L.t("rep.vat"),
        L.t("rep.incl_vat"),
    ]
    if has_fixed:
        header.append(L.t("rep.fixed_short"))

    data = [
        [
            Paragraph(f"<b>{h.replace(chr(10), '<br/>')}</b>", st["cell"])
            for h in header
        ]
    ]
    for row in report.rows:
        line = [
            row.start.strftime("%Y-%m-%d %H:%M"),
            L.n(row.consumption, 3),
            L.n(row.unit_price_incl_vat, 4),
            L.n(row.spot_cost_ex_vat),
            L.n(row.spot_vat),
            L.n(row.spot_cost_incl_vat),
        ]
        if has_fixed:
            line.append(L.n(row.fixed_cost_incl_vat))
        data.append(line)

    total = [
        L.t("rep.total"),
        L.n(report.total_consumption, 3),
        "",
        L.n(report.total_spot_ex_vat),
        L.n(report.total_spot_vat),
        L.n(report.total_spot_incl_vat),
    ]
    if has_fixed:
        total.append(L.n(report.total_fixed_incl_vat))
    data.append(total)

    widths = [34 * mm, 20 * mm, 24 * mm, 24 * mm, 20 * mm, 24 * mm]
    if has_fixed:
        widths.append(26 * mm)

    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.7, ACCENT),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.7, ACCENT),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, ZEBRA]),
            ]
        )
    )
    return table


def _page_furniture(L: Loc):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(16 * mm, 12 * mm, L.t("rep.footer"))
        canvas.drawRightString(
            A4[0] - 16 * mm, 12 * mm, L.t("rep.page", page=doc.page)
        )
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(16 * mm, 15 * mm, A4[0] - 16 * mm, 15 * mm)
        canvas.restoreState()

    return draw


def to_pdf(report: Report, locale: str = DEFAULT_LOCALE) -> bytes:
    L = Loc(locale)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title=f"{L.t('rep.title')} {report.start:%Y-%m-%d} - {report.end:%Y-%m-%d}",
        author=L.t("rep.csv_title"),
    )
    st = _styles()
    story: list = [
        Paragraph(L.t("rep.title"), st["title"]),
        Paragraph(home_label(report, locale), st["sub"]),
        Spacer(1, 9),
        _headline_table(report, st, L),
        Spacer(1, 11),
        Paragraph(L.t("rep.details"), st["h2"]),
        _meta_table(report, st, L),
        Spacer(1, 10),
        Paragraph(L.t("rep.cost_summary"), st["h2"]),
        _summary_table(report, st, L),
    ]

    rendered_warnings = report.rendered_warnings(locale)
    if rendered_warnings:
        story += [Spacer(1, 10), Paragraph(L.t("rep.notes"), st["h2"])]
        for warning in rendered_warnings:
            story.append(Paragraph(f"&bull; {warning}", st["note"]))

    story += [Spacer(1, 6), Paragraph(L.t("rep.disclaimer"), st["note"])]

    if report.rows:
        story += [
            PageBreak(),
            Paragraph(L.t("rep.hourly_detail"), st["h2"]),
            _detail_table(report, st, L),
        ]

    furniture = _page_furniture(L)
    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    return buffer.getvalue()
