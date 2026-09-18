"""Tests for the translation catalogue and localized output."""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.i18n import (  # noqa: E402
    CATALOGUE,
    DEFAULT_LOCALE,
    LOCALES,
    LocalizedError,
    format_number,
    format_percent,
    normalize,
    t,
    warning_text,
)

STATIC = Path(__file__).resolve().parents[1] / "app" / "static"


# ---------------------------------------------------------- catalogue -----
def test_every_locale_defines_the_same_keys():
    reference = set(CATALOGUE[DEFAULT_LOCALE])
    for locale in LOCALES:
        assert set(CATALOGUE[locale]) == reference, f"{locale} key set differs"


def test_placeholders_match_across_locales():
    """A translation must not invent or drop a {placeholder}."""
    for key, template in CATALOGUE[DEFAULT_LOCALE].items():
        expected = set(re.findall(r"\{(\w+)\}", template))
        for locale in LOCALES:
            actual = set(re.findall(r"\{(\w+)\}", CATALOGUE[locale][key]))
            assert actual == expected, f"{locale}:{key} placeholders {actual}"


def test_no_translation_is_left_as_the_english_string():
    """Catches keys that were added to 'nb' by copy-paste and never translated."""
    # Terms that are legitimately identical in both languages.
    allowed = {
        "rep.kwh", "rep.vat", "rep.spot", "rep.currency", "rep.total",
        "rep.spot_currency", "rep.hour", "rep.note", "rep.notes",
        "rep.unit_price_short", "rep.fixed_vat_extra", "rep.per_kwh_incl",
        "rep.per_kwh_excl", "rep.fixed_detail", "rep.page",
    }
    identical = [
        key
        for key, text in CATALOGUE["nb"].items()
        if text == CATALOGUE["en"][key] and key not in allowed
    ]
    assert not identical, f"untranslated keys: {identical}"


# ------------------------------------------------------------ lookup ------
@pytest.mark.parametrize(
    "value,expected",
    [
        ("nb", "nb"), ("nb-NO", "nb"), ("NB_no", "nb"), ("no", "nb"), ("nn", "nb"),
        ("en", "en"), ("en-GB", "en"), ("de", "en"), ("", "en"), (None, "en"),
        ("nb-NO,nb;q=0.9,en;q=0.8", "nb"),
    ],
)
def test_normalize_maps_tags_onto_supported_locales(value, expected):
    assert normalize(value) == expected


def test_unknown_key_falls_back_to_the_key_itself():
    assert t("nb", "no.such.key") == "no.such.key"


def test_missing_translation_falls_back_to_english():
    assert t("de", "rep.home") == CATALOGUE["en"]["rep.home"]


def test_substitution_survives_a_missing_parameter():
    """A missing param must not raise, and must not discard the others."""
    text = t("en", "err.lookback", hours=5)  # {limit} deliberately absent
    assert "5 hours ago" in text
    assert "{limit}" in text


# ------------------------------------------------------------ numbers -----
def test_norwegian_numbers_use_a_comma_decimal_mark():
    assert format_number(1234.5, 2, "nb") == "1 234,50"
    assert format_number(1234.5, 2, "en") == "1 234.50"


def test_format_number_handles_none():
    assert format_number(None, 2, "nb") == "-"


def test_percentages_follow_the_locale():
    assert format_percent(0.25, "nb") == "25,0 %"
    assert format_percent(0.25, "en") == "25.0 %"


# ----------------------------------------------------------- warnings -----
def test_warning_text_formats_a_rate_parameter():
    text = warning_text("nb", "warn.vat_assumed", {"rate": 0.25})
    assert "25" in text and "%" in text
    assert "MVA" in text


def test_warning_text_renders_counts():
    text = warning_text("nb", "warn.partial_hours", {"missing": 3, "expected": 24})
    assert "3 av 24" in text


# ------------------------------------------------------------- errors -----
def test_localized_error_renders_per_locale():
    exc = LocalizedError("err.negative_price", status_code=400)
    assert exc.localized("en") == "The fixed price cannot be negative."
    assert exc.localized("nb") == "Fastprisen kan ikke være negativ."
    # str() stays English so logs and tracebacks are stable.
    assert str(exc) == exc.localized("en")


def test_localized_error_keeps_its_parameters():
    exc = LocalizedError("err.home_not_found", status_code=404, home_id="abc")
    assert "abc" in exc.localized("en")
    assert "abc" in exc.localized("nb")


# --------------------------------------------------- frontend catalogue ---
def _js_locale_keys(block: str) -> set[str]:
    return set(re.findall(r'^\s{4}"([\w.]+)":', block, re.M))


def test_frontend_catalogue_has_the_same_keys_in_both_locales():
    source = (STATIC / "i18n.js").read_text()
    english = source.split("  en: {", 1)[1].split("\n  nb: {", 1)[0]
    norwegian = source.split("  nb: {", 1)[1]
    assert _js_locale_keys(english) == _js_locale_keys(norwegian)


def test_every_data_i18n_attribute_has_a_frontend_key():
    html = (STATIC / "index.html").read_text()
    source = (STATIC / "i18n.js").read_text()
    english = source.split("  en: {", 1)[1].split("\n  nb: {", 1)[0]
    defined = _js_locale_keys(english)

    used = set(re.findall(r'data-i18n(?:-placeholder)?="([\w.]+)"', html))
    assert used, "no data-i18n attributes found"
    assert used <= defined, f"undefined keys in index.html: {sorted(used - defined)}"


def test_app_js_only_translates_keys_that_exist():
    app_js = (STATIC / "app.js").read_text()
    source = (STATIC / "i18n.js").read_text()
    english = source.split("  en: {", 1)[1].split("\n  nb: {", 1)[0]
    defined = _js_locale_keys(english)

    # (?<![\w.]) so that getItem(" / createElement(" do not look like t(".
    used = set(re.findall(r'(?<![\w.])t\(\s*"([\w.]+)"', app_js))
    assert used, "no t() calls found"
    assert used <= defined, f"undefined keys in app.js: {sorted(used - defined)}"
