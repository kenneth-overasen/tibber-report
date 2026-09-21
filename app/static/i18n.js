"use strict";

/* UI strings. Keys used by data-i18n attributes in index.html and by app.js.
   Report labels live in the server-side catalogue (app/i18n.py) instead. */
const I18N = {
  en: {
    "ui.brand": "Tibber consumption report",
    "ui.language": "Language",
    "ui.home": "Home",
    "ui.homes_loading": "Loading homes from Tibber…",
    "ui.homes_count": "{count} home(s) on this account.",
    "ui.homes_none": "This Tibber account has no homes.",
    "ui.homes_error": "Could not load homes: {error}",
    "ui.from": "From",
    "ui.to": "To",
    "ui.to_note": "(exclusive)",
    "ui.fixed_legend": "Fixed price override",
    "ui.optional": "(optional)",
    "ui.fixed_enable": "Use a fixed price per kWh",
    "ui.price_per_kwh": "Price per kWh",
    "ui.fixed_hint":
      "A fixed price is a flat price per kWh; VAT is not added to it. It is " +
      "compared against what the spot price actually costs, incl. VAT.",
    "ui.quick_ranges": "Quick ranges:",
    "ui.yesterday": "Yesterday",
    "ui.last7": "Last 7 days",
    "ui.this_month": "This month",
    "ui.last_month": "Last month",
    "ui.generate": "Generate report",
    "ui.download_pdf": "Download PDF",
    "ui.download_csv": "Download CSV",
    "ui.download_json": "Download JSON",
    "ui.api_token": "API token",
    "ui.token_hint":
      "No TIBBER_TOKEN is configured on the server. Paste a token to use for " +
      "this browser session only — it is not stored on the server.",
    "ui.token_placeholder": "Tibber personal access token",
    "ui.token_save": "Use token",
    "ui.token_env": "Token from environment",
    "ui.token_session": "Token from this session",
    "ui.token_none": "No token configured",
    "ui.loading": "Fetching consumption from Tibber…",
    "ui.report": "Report",
    "ui.cost_summary": "Cost summary",
    "ui.hourly_detail": "Hourly detail",
    "ui.hide_empty": "Hide hours with no consumption",
    "ui.no_hours": "No hours to show.",
    "ui.settings_saved": "Settings are remembered in this browser.",
    "ui.reset": "Reset saved settings",
    // summary + tiles
    "ui.tile_consumption": "Consumption",
    "ui.tile_spot_incl": "Spot incl. VAT",
    "ui.tile_spot_excl": "Spot excl. VAT",
    "ui.tile_fixed": "Fixed total",
    "ui.tile_avg": "Avg. price incl. VAT",
    "ui.tile_diff": "Fixed − spot",
    "ui.col_hour": "Hour",
    "ui.col_kwh": "kWh",
    "ui.col_unit_price": "{currency}/kWh incl. VAT",
    "ui.col_excl": "Excl. VAT ({currency})",
    "ui.col_vat": "VAT ({currency})",
    "ui.col_incl": "Incl. VAT ({currency})",
    "ui.col_fixed": "Fixed ({currency})",
    "ui.row_excl": "Excl. VAT",
    "ui.row_vat_rate": "VAT ({rate})",
    "ui.row_total": "Total cost",
    "ui.total": "TOTAL",
    "ui.total_all": "TOTAL (all hours)",
    "ui.head_spot": "Spot ({currency})",
    "ui.head_fixed": "Fixed ({currency})",
    "ui.sub_hours": "{count} hour(s) with data",
    "ui.sub_spot_vat": "spot VAT {rate} ({source})",
    "ui.sub_fixed_price": "fixed {price} {currency}/kWh, VAT-free",
    "ui.vat_from_api": "from API data",
    "ui.vat_assumed": "assumed",
    // client-side validation
    "err.pick_dates": "Pick both a start and an end date.",
    "err.pick_price": "Enter a fixed price per kWh, or untick the override.",
    "err.http": "Request failed with HTTP {status}.",
  },

  nb: {
    "ui.brand": "Tibber forbruksrapport",
    "ui.language": "Språk",
    "ui.home": "Bolig",
    "ui.homes_loading": "Henter boliger fra Tibber…",
    "ui.homes_count": "{count} bolig(er) på denne kontoen.",
    "ui.homes_none": "Denne Tibber-kontoen har ingen boliger.",
    "ui.homes_error": "Kunne ikke hente boliger: {error}",
    "ui.from": "Fra",
    "ui.to": "Til",
    "ui.to_note": "(eksklusiv)",
    "ui.fixed_legend": "Fastpris (overstyring)",
    "ui.optional": "(valgfritt)",
    "ui.fixed_enable": "Bruk fastpris per kWh",
    "ui.price_per_kwh": "Pris per kWh",
    "ui.fixed_hint":
      "Fastpris er en flat pris per kWh; MVA legges ikke til. Den " +
      "sammenlignes med hva spotprisen faktisk koster, inkl. MVA.",
    "ui.quick_ranges": "Hurtigvalg:",
    "ui.yesterday": "I går",
    "ui.last7": "Siste 7 dager",
    "ui.this_month": "Denne måneden",
    "ui.last_month": "Forrige måned",
    "ui.generate": "Lag rapport",
    "ui.download_pdf": "Last ned PDF",
    "ui.download_csv": "Last ned CSV",
    "ui.download_json": "Last ned JSON",
    "ui.api_token": "API-token",
    "ui.token_hint":
      "Ingen TIBBER_TOKEN er konfigurert på serveren. Lim inn en token som " +
      "kun brukes i denne nettleserøkten — den lagres ikke på serveren.",
    "ui.token_placeholder": "Tibber personlig tilgangstoken",
    "ui.token_save": "Bruk token",
    "ui.token_env": "Token fra miljøvariabel",
    "ui.token_session": "Token fra denne økten",
    "ui.token_none": "Ingen token konfigurert",
    "ui.loading": "Henter forbruk fra Tibber…",
    "ui.report": "Rapport",
    "ui.cost_summary": "Kostnadssammendrag",
    "ui.hourly_detail": "Detaljer per time",
    "ui.hide_empty": "Skjul timer uten forbruk",
    "ui.no_hours": "Ingen timer å vise.",
    "ui.settings_saved": "Innstillingene huskes i denne nettleseren.",
    "ui.reset": "Nullstill lagrede innstillinger",
    "ui.tile_consumption": "Forbruk",
    "ui.tile_spot_incl": "Spot inkl. MVA",
    "ui.tile_spot_excl": "Spot eks. MVA",
    "ui.tile_fixed": "Fastpris totalt",
    "ui.tile_avg": "Snittpris inkl. MVA",
    "ui.tile_diff": "Fastpris − spot",
    "ui.col_hour": "Time",
    "ui.col_kwh": "kWh",
    "ui.col_unit_price": "{currency}/kWh inkl. MVA",
    "ui.col_excl": "Eks. MVA ({currency})",
    "ui.col_vat": "MVA ({currency})",
    "ui.col_incl": "Inkl. MVA ({currency})",
    "ui.col_fixed": "Fastpris ({currency})",
    "ui.row_excl": "Eks. MVA",
    "ui.row_vat_rate": "MVA ({rate})",
    "ui.row_total": "Total kostnad",
    "ui.total": "TOTALT",
    "ui.total_all": "TOTALT (alle timer)",
    "ui.head_spot": "Spot ({currency})",
    "ui.head_fixed": "Fastpris ({currency})",
    "ui.sub_hours": "{count} time(r) med data",
    "ui.sub_spot_vat": "spot-MVA {rate} ({source})",
    "ui.sub_fixed_price": "fastpris {price} {currency}/kWh, uten MVA",
    "ui.vat_from_api": "fra API-data",
    "ui.vat_assumed": "antatt",
    "err.pick_dates": "Velg både start- og sluttdato.",
    "err.pick_price":
      "Skriv inn en fastpris per kWh, eller fjern haken for overstyring.",
    "err.http": "Forespørselen feilet med HTTP {status}.",
  },
};

const LOCALE_TAGS = { en: "en-GB", nb: "nb-NO" };
const LANGUAGE_NAMES = { en: "English", nb: "Norsk" };

function normalizeLocale(value) {
  if (!value) return "en";
  const primary = String(value).toLowerCase().replace("_", "-").split("-")[0];
  if (["nb", "nn", "no"].includes(primary)) return "nb";
  return I18N[primary] ? primary : "en";
}

/** Look up `key`, substituting {placeholders}; falls back to English. */
function translate(locale, key, params) {
  const loc = normalizeLocale(locale);
  const template = (I18N[loc] && I18N[loc][key]) ?? I18N.en[key] ?? key;
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, name) =>
    Object.prototype.hasOwnProperty.call(params, name) ? params[name] : match
  );
}
