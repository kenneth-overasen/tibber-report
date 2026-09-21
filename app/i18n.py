"""Translation catalogue and the localized-error base class.

Everything user-visible -- UI chrome, report labels, warnings and error
messages -- is keyed here so the same text can be produced in English or
Norwegian Bokmal.  Server code raises errors by *key*, never by sentence, and
the sentence is rendered once the request locale is known.
"""
from __future__ import annotations

DEFAULT_LOCALE = "en"
LOCALES = ("en", "nb")

LOCALE_TAGS = {"en": "en-GB", "nb": "nb-NO"}

# Decimal and thousands separators used by the CSV and PDF exporters.
NUMBER_FORMATS = {
    "en": {"decimal": ".", "thousands": " "},
    "nb": {"decimal": ",", "thousands": " "},
}

CATALOGUE: dict[str, dict[str, str]] = {
    # ------------------------------------------------------------ report --
    "en": {
        "rep.title": "Electricity consumption report",
        "rep.csv_title": "Tibber consumption report",
        "rep.home": "Home",
        "rep.period": "Period",
        "rep.period_from": "Period from",
        "rep.period_to": "Period to",
        "rep.to": "to",
        "rep.from_col": "From",
        "rep.to_col": "To",
        "rep.generated": "Generated",
        "rep.currency": "Currency",
        "rep.vat_rate": "VAT rate",
        "rep.derived": "derived from data",
        "rep.assumed": "assumed",
        "rep.fixed_override": "Fixed price override",
        "rep.per_kwh_incl": "{price} {currency}/kWh incl. VAT",
        "rep.per_kwh_excl": "{price} {currency}/kWh excl. VAT",
        "rep.fixed_detail": "{price} {currency}/kWh (VAT does not apply)",
        "rep.details": "Details",
        "rep.summary": "Summary",
        "rep.cost_summary": "Cost summary",
        "rep.hours_with_data": "Hours with data",
        "rep.total_consumption": "Total consumption (kWh)",
        "rep.spot_total_incl": "Spot total incl. VAT ({currency})",
        "rep.spot_total_excl": "Spot total excl. VAT ({currency})",
        "rep.spot_vat": "Spot VAT ({currency})",
        "rep.avg_price": "Average spot price incl. VAT ({currency}/kWh)",
        "rep.fixed_total": "Fixed total ({currency})",
        "rep.difference": "Difference, fixed - spot incl. VAT ({currency})",
        "rep.hourly_detail": "Hourly detail",
        "rep.hour": "Hour",
        "rep.kwh": "kWh",
        "rep.unit_price_incl": "Unit price incl. VAT ({currency}/kWh)",
        "rep.unit_price_excl": "Unit price excl. VAT ({currency}/kWh)",
        "rep.unit_price_short": "{currency}/kWh\nincl. VAT",
        "rep.spot_cost_incl": "Spot cost incl. VAT ({currency})",
        "rep.spot_cost_excl": "Spot cost excl. VAT ({currency})",
        "rep.spot_cost_vat": "Spot VAT ({currency})",
        "rep.fixed_cost": "Fixed cost ({currency})",
        "rep.fixed_short": "Fixed",
        "rep.excl_vat": "Excl. VAT",
        "rep.vat": "VAT",
        "rep.incl_vat": "Incl. VAT",
        "rep.spot": "Spot",
        "rep.fixed": "Fixed",
        "rep.spot_currency": "Spot ({currency})",
        "rep.fixed_currency": "Fixed ({currency})",
        "rep.total_cost": "Total cost",
        "rep.total": "TOTAL",
        "rep.consumption": "Consumption",
        "rep.spot_tile": "Spot total incl. VAT",
        "rep.fixed_tile": "Fixed total",
        "rep.price_tile": "Fixed price",
        "rep.avg_tile": "Avg. price incl. VAT",
        "rep.difference_tile": "Fixed - spot",
        "rep.notes": "Notes",
        "rep.note": "Note",
        "rep.disclaimer": (
            "Prices are Tibber spot prices for energy. Grid rent, fixed monthly "
            "fees and any production reward are not included."
        ),
        "rep.disclaimer_fixed": (
            "Costs are the entered fixed price applied to metered consumption, "
            "for energy only. Grid rent, fixed monthly fees and any production "
            "reward are not included."
        ),
        "rep.page": "Page {page}",
        "rep.footer": "Generated from the Tibber API",
        "rep.unknown_address": "Unknown address",
        # ------------------------------------------------------ warnings --
        "warn.no_data": (
            "No hourly consumption data was returned for this period. Tibber only "
            "has data from meters it reads; very recent hours and dates before the "
            "subscription started will be empty."
        ),
        "warn.partial_hours": (
            "{missing} of {expected} hours in the period have no data and are "
            "excluded from the totals."
        ),
        "warn.earliest": (
            "The API returned data only from {timestamp} onwards; earlier hours in "
            "the period could not be retrieved."
        ),
        "warn.missing_price": (
            "{count} hour(s) had consumption but no price from the API and "
            "contribute 0 to the spot total."
        ),
        "warn.vat_assumed": (
            "VAT rate could not be derived from the data; assuming {rate}."
        ),
        # -------------------------------------------------------- errors --
        "err.no_token": (
            "No Tibber API token configured. Set the TIBBER_TOKEN environment "
            "variable, or enter a token in the UI."
        ),
        "err.token_rejected": "Tibber rejected the API token.",
        "err.rate_limited": (
            "Rate limited by the Tibber API. Wait a moment and try again."
        ),
        "err.unreachable": "Could not reach the Tibber API: {error}",
        "err.http_status": "Tibber API returned HTTP {status}: {body}",
        "err.non_json": "Tibber API returned a non-JSON response.",
        "err.graphql": "Tibber API error: {messages}",
        "err.no_data_returned": "Tibber API returned no data.",
        "err.no_homes": "This Tibber account has no homes.",
        "err.home_not_found": "No home with id '{home_id}' on this account.",
        "err.postal_not_found": (
            "No home with postal code '{postal_code}'. Available: {available}."
        ),
        "err.postal_ambiguous": (
            "{count} homes share postal code '{postal_code}'. Select one by home "
            "id instead."
        ),
        "err.select_home": (
            "This account has several homes; specify home_id or postal_code."
        ),
        "err.end_before_start": "The end of the period must be after the start.",
        "err.future_start": "The period starts in the future.",
        "err.lookback": (
            "The period starts {hours} hours ago, beyond the configured limit of "
            "{limit} hours. Raise TIBBER_MAX_LOOKBACK_HOURS to allow it."
        ),
        "err.negative_price": "The fixed price cannot be negative.",
        "err.unknown_timezone": "Unknown time zone '{name}'.",
        "err.bad_timestamp": "Could not parse timestamp '{value}'.",
        "err.no_offset": "Timestamp '{value}' has no UTC offset.",
        "err.bad_local": (
            "Could not parse '{value}'; expected YYYY-MM-DD or YYYY-MM-DDTHH:MM."
        ),
    },
    "nb": {
        "rep.title": "Rapport for strømforbruk",
        "rep.csv_title": "Tibber forbruksrapport",
        "rep.home": "Bolig",
        "rep.period": "Periode",
        "rep.period_from": "Periode fra",
        "rep.period_to": "Periode til",
        "rep.to": "til",
        "rep.from_col": "Fra",
        "rep.to_col": "Til",
        "rep.generated": "Generert",
        "rep.currency": "Valuta",
        "rep.vat_rate": "MVA-sats",
        "rep.derived": "utledet fra data",
        "rep.assumed": "antatt",
        "rep.fixed_override": "Fastpris (overstyring)",
        "rep.per_kwh_incl": "{price} {currency}/kWh inkl. MVA",
        "rep.per_kwh_excl": "{price} {currency}/kWh eks. MVA",
        "rep.fixed_detail": "{price} {currency}/kWh (MVA gjelder ikke)",
        "rep.details": "Detaljer",
        "rep.summary": "Sammendrag",
        "rep.cost_summary": "Kostnadssammendrag",
        "rep.hours_with_data": "Timer med data",
        "rep.total_consumption": "Totalt forbruk (kWh)",
        "rep.spot_total_incl": "Spot totalt inkl. MVA ({currency})",
        "rep.spot_total_excl": "Spot totalt eks. MVA ({currency})",
        "rep.spot_vat": "MVA spot ({currency})",
        "rep.avg_price": "Gjennomsnittlig spotpris inkl. MVA ({currency}/kWh)",
        "rep.fixed_total": "Fastpris totalt ({currency})",
        "rep.difference": "Differanse, fastpris - spot inkl. MVA ({currency})",
        "rep.hourly_detail": "Detaljer per time",
        "rep.hour": "Time",
        "rep.kwh": "kWh",
        "rep.unit_price_incl": "Enhetspris inkl. MVA ({currency}/kWh)",
        "rep.unit_price_excl": "Enhetspris eks. MVA ({currency}/kWh)",
        "rep.unit_price_short": "{currency}/kWh\ninkl. MVA",
        "rep.spot_cost_incl": "Spotkostnad inkl. MVA ({currency})",
        "rep.spot_cost_excl": "Spotkostnad eks. MVA ({currency})",
        "rep.spot_cost_vat": "MVA spot ({currency})",
        "rep.fixed_cost": "Fastpriskostnad ({currency})",
        "rep.fixed_short": "Fastpris",
        "rep.excl_vat": "Eks. MVA",
        "rep.vat": "MVA",
        "rep.incl_vat": "Inkl. MVA",
        "rep.spot": "Spot",
        "rep.fixed": "Fastpris",
        "rep.spot_currency": "Spot ({currency})",
        "rep.fixed_currency": "Fastpris ({currency})",
        "rep.total_cost": "Total kostnad",
        "rep.total": "TOTALT",
        "rep.consumption": "Forbruk",
        "rep.spot_tile": "Spot totalt inkl. MVA",
        "rep.fixed_tile": "Fastpris totalt",
        "rep.price_tile": "Fastpris",
        "rep.avg_tile": "Snittpris inkl. MVA",
        "rep.difference_tile": "Fastpris - spot",
        "rep.notes": "Merknader",
        "rep.note": "Merknad",
        "rep.disclaimer": (
            "Prisene er Tibbers spotpriser for energi. Nettleie, faste "
            "månedsgebyrer og eventuell produksjonsgodtgjørelse er ikke inkludert."
        ),
        "rep.disclaimer_fixed": (
            "Kostnadene er den oppgitte fastprisen anvendt på målt forbruk, kun "
            "for energi. Nettleie, faste månedsgebyrer og eventuell "
            "produksjonsgodtgjørelse er ikke inkludert."
        ),
        "rep.page": "Side {page}",
        "rep.footer": "Generert fra Tibber-API-et",
        "rep.unknown_address": "Ukjent adresse",
        # ------------------------------------------------------ warnings --
        "warn.no_data": (
            "Ingen timesdata for forbruk ble returnert for denne perioden. Tibber "
            "har kun data fra målere de leser av; svært nylige timer og datoer før "
            "abonnementet startet vil være tomme."
        ),
        "warn.partial_hours": (
            "{missing} av {expected} timer i perioden mangler data og er utelatt "
            "fra totalene."
        ),
        "warn.earliest": (
            "API-et returnerte data først fra {timestamp}; tidligere timer i "
            "perioden kunne ikke hentes."
        ),
        "warn.missing_price": (
            "{count} time(r) hadde forbruk, men ingen pris fra API-et, og bidrar "
            "med 0 til spot-totalen."
        ),
        "warn.vat_assumed": (
            "MVA-satsen kunne ikke utledes fra dataene; antar {rate}."
        ),
        # -------------------------------------------------------- errors --
        "err.no_token": (
            "Ingen Tibber API-token er konfigurert. Sett miljøvariabelen "
            "TIBBER_TOKEN, eller skriv inn en token i grensesnittet."
        ),
        "err.token_rejected": "Tibber avviste API-tokenet.",
        "err.rate_limited": (
            "For mange forespørsler mot Tibber-API-et. Vent litt og prøv igjen."
        ),
        "err.unreachable": "Kunne ikke nå Tibber-API-et: {error}",
        "err.http_status": "Tibber-API-et svarte med HTTP {status}: {body}",
        "err.non_json": "Tibber-API-et returnerte et svar som ikke er JSON.",
        "err.graphql": "Feil fra Tibber-API-et: {messages}",
        "err.no_data_returned": "Tibber-API-et returnerte ingen data.",
        "err.no_homes": "Denne Tibber-kontoen har ingen boliger.",
        "err.home_not_found": "Ingen bolig med id '{home_id}' på denne kontoen.",
        "err.postal_not_found": (
            "Ingen bolig med postnummer '{postal_code}'. Tilgjengelige: {available}."
        ),
        "err.postal_ambiguous": (
            "{count} boliger deler postnummer '{postal_code}'. Velg én ved hjelp "
            "av bolig-id i stedet."
        ),
        "err.select_home": (
            "Denne kontoen har flere boliger; oppgi home_id eller postal_code."
        ),
        "err.end_before_start": "Slutten av perioden må være etter starten.",
        "err.future_start": "Perioden starter fram i tid.",
        "err.lookback": (
            "Perioden starter {hours} timer tilbake i tid, utover den konfigurerte "
            "grensen på {limit} timer. Øk TIBBER_MAX_LOOKBACK_HOURS for å tillate "
            "det."
        ),
        "err.negative_price": "Fastprisen kan ikke være negativ.",
        "err.unknown_timezone": "Ukjent tidssone '{name}'.",
        "err.bad_timestamp": "Kunne ikke tolke tidsstempelet '{value}'.",
        "err.no_offset": "Tidsstempelet '{value}' mangler UTC-forskyvning.",
        "err.bad_local": (
            "Kunne ikke tolke '{value}'; forventet ÅÅÅÅ-MM-DD eller "
            "ÅÅÅÅ-MM-DDTTT:MM."
        ),
    },
}


class _Forgiving(dict):
    """Leaves unknown placeholders as-is instead of raising."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def normalize(locale: str | None) -> str:
    """Map anything the client sends onto a supported locale."""
    if not locale:
        return DEFAULT_LOCALE
    tag = locale.strip().lower().replace("_", "-").split(",")[0].split(";")[0]
    if not tag:
        return DEFAULT_LOCALE
    primary = tag.split("-")[0]
    # Norwegian has three tags in the wild: nb, nn and the macrolanguage no.
    if primary in ("nb", "nn", "no"):
        return "nb"
    if primary in LOCALES:
        return primary
    return DEFAULT_LOCALE


def t(locale: str | None, key: str, **params) -> str:
    """Look a key up, falling back to English and then to the key itself."""
    loc = normalize(locale)
    template = CATALOGUE.get(loc, {}).get(key)
    if template is None:
        template = CATALOGUE[DEFAULT_LOCALE].get(key, key)
    if not params:
        return template
    try:
        return template.format_map(_Forgiving(params))
    except (IndexError, ValueError):
        return template


def format_number(value: float | None, digits: int, locale: str | None) -> str:
    """Group thousands and pick the decimal mark the locale expects."""
    if value is None:
        return "-"
    fmt = NUMBER_FORMATS.get(normalize(locale), NUMBER_FORMATS[DEFAULT_LOCALE])
    text = f"{value:,.{digits}f}"
    # Python always emits "," for groups and "." for the decimal mark; swap
    # both at once via a placeholder so neither replacement eats the other.
    return (
        text.replace(",", "\x00")
        .replace(".", fmt["decimal"])
        .replace("\x00", fmt["thousands"])
    )


def format_percent(value: float, locale: str | None, digits: int = 1) -> str:
    return f"{format_number(value * 100, digits, locale)} %"


class LocalizedError(Exception):
    """An error that knows its catalogue key, so it can be rendered later."""

    def __init__(self, code: str, status_code: int = 400, **params):
        self.code = code
        self.params = params
        self.status_code = status_code
        super().__init__(t(DEFAULT_LOCALE, code, **params))

    def localized(self, locale: str | None) -> str:
        return t(locale, self.code, **self.params)


def warning_text(locale: str | None, code: str, params: dict) -> str:
    """Render one structured warning, formatting numeric params per locale."""
    rendered = dict(params)
    rate = rendered.get("rate")
    if isinstance(rate, (int, float)):
        rendered["rate"] = format_percent(float(rate), locale, 0)
    return t(locale, code, **rendered)
