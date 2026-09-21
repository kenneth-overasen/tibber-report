"use strict";

const $ = (id) => document.getElementById(id);
const TOKEN_KEY = "tibber.token";
const PREFS_KEY = "tibber.prefs.v1";

let state = {
  config: null,
  homes: [],
  report: null,
  locale: "en",
};

const t = (key, params) => translate(state.locale, key, params);
const localeTag = () => LOCALE_TAGS[state.locale] || "en-GB";

/* ---------------------------------------------------------- persistence -- */
/* Preferences live in localStorage so they survive a browser restart; the API
   token lives in sessionStorage so it does not. Both are wrapped because
   private browsing can make either accessor throw. */
function loadPrefs() {
  try {
    return JSON.parse(localStorage.getItem(PREFS_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function savePrefs() {
  const prefs = {
    lang: state.locale,
    homeId: $("home").value || null,
    startTime: $("start-time").value,
    endTime: $("end-time").value,
    fixedEnabled: $("fixed-enabled").checked,
    fixedPrice: $("fixed-price").value,
    hideEmpty: $("hide-empty").checked,
  };
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* storage unavailable: settings simply are not remembered */
  }
}

function clearPrefs() {
  try {
    localStorage.removeItem(PREFS_KEY);
  } catch {
    /* nothing to do */
  }
}

function sessionToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) || null;
  } catch {
    return null;
  }
}

function setSessionToken(value) {
  try {
    if (value) sessionStorage.setItem(TOKEN_KEY, value);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* private mode: the token lives only for this page load */
  }
}

/* ------------------------------------------------------------ helpers -- */
const fmt = (value, digits = 2) =>
  value === null || value === undefined || Number.isNaN(value)
    ? "–"
    : value.toLocaleString(localeTag(), {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      });

const pct = (value, digits = 1) =>
  `${(value * 100).toLocaleString(localeTag(), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })} %`;

const hourLabel = (iso) =>
  new Date(iso).toLocaleString(localeTag(), {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });

function showError(message) {
  const box = $("error");
  box.textContent = message;
  box.classList.remove("hidden");
}

const clearError = () => $("error").classList.add("hidden");
const pad = (n) => String(n).padStart(2, "0");
const dateValue = (d) =>
  `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/* ------------------------------------------------------------ language -- */
function applyLanguage() {
  document.documentElement.lang = state.locale;
  document.title = t("ui.brand");

  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-placeholder]")) {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  }

  updateTokenPill();
  updateHomeHint();
  if (state.report) renderReport(state.report);
}

function updateTokenPill() {
  const pill = $("token-state");
  pill.classList.remove("warn");
  if (state.config?.tokenConfigured) {
    pill.textContent = t("ui.token_env");
  } else if (sessionToken()) {
    pill.textContent = t("ui.token_session");
  } else {
    pill.textContent = t("ui.token_none");
    pill.classList.add("warn");
  }
}

function updateHomeHint() {
  const hint = $("home-hint");
  if (state.homesError) {
    hint.textContent = t("ui.homes_error", { error: state.homesError });
  } else if (state.homes.length) {
    hint.textContent = t("ui.homes_count", { count: state.homes.length });
  } else if (state.homesLoaded) {
    hint.textContent = t("ui.homes_none");
  } else {
    hint.textContent = t("ui.homes_loading");
  }
}

/* -------------------------------------------------------- request body -- */
function buildRequest() {
  const startDate = $("start-date").value;
  const endDate = $("end-date").value;
  if (!startDate || !endDate) throw new Error(t("err.pick_dates"));

  const body = {
    home_id: $("home").value || null,
    start: `${startDate}T${$("start-time").value || "00:00"}`,
    end: `${endDate}T${$("end-time").value || "00:00"}`,
    lang: state.locale,
  };

  if ($("fixed-enabled").checked) {
    const price = parseFloat($("fixed-price").value);
    if (!Number.isFinite(price)) throw new Error(t("err.pick_price"));
    body.fixed_price = price;
  }

  const token = sessionToken();
  if (token) body.token = token;
  return body;
}

async function postJson(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Lang": state.locale },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    let detail = t("err.http", { status: response.status });
    try {
      const payload = await response.json();
      if (payload.detail) {
        detail =
          typeof payload.detail === "string"
            ? payload.detail
            : JSON.stringify(payload.detail);
      }
    } catch {
      /* keep the generic message */
    }
    throw new Error(detail);
  }
  return response;
}

/* --------------------------------------------------------- rendering ---- */
function renderTiles(report) {
  const cur = report.currency;
  const s = report.summary;
  const tiles = [
    { k: t("ui.tile_consumption"), v: fmt(s.totalConsumption, 2), u: "kWh" },
    { k: t("ui.tile_spot_incl"), v: fmt(s.spot.inclVat), u: cur },
    { k: t("ui.tile_spot_excl"), v: fmt(s.spot.exVat), u: cur },
    {
      k: t("ui.tile_avg"),
      v: fmt(s.averageSpotPriceInclVat, 4),
      u: `${cur}/kWh`,
    },
  ];

  if (s.fixed) {
    tiles.splice(3, 0, { k: t("ui.tile_fixed"), v: fmt(s.fixed.total), u: cur });
    const diff = s.difference ?? 0;
    tiles.push({
      k: t("ui.tile_diff"),
      v: `${diff >= 0 ? "+" : "−"}${fmt(Math.abs(diff))}`,
      u: cur,
      cls: diff >= 0 ? "pos" : "neg",
    });
  }

  $("tiles").innerHTML = tiles
    .map(
      (tile) => `<div class="tile"><div class="k">${tile.k}</div>
        <div class="v ${tile.cls || ""}">${tile.v}<span class="u">${tile.u}</span></div></div>`
    )
    .join("");
}

function renderSummary(report) {
  const cur = report.currency;
  const s = report.summary;
  const hasFixed = Boolean(s.fixed);

  const head = `<thead><tr><th></th><th>${t("ui.head_spot", {
    currency: cur,
  })}</th>${hasFixed ? `<th>${t("ui.head_fixed", { currency: cur })}</th>` : ""}</tr></thead>`;

  const row = (label, spot, fixed) =>
    `<tr><td>${label}</td><td>${fmt(spot)}</td>${
      hasFixed ? `<td>${fmt(fixed)}</td>` : ""
    }</tr>`;

  // The VAT split belongs to the spot price only: a fixed price is VAT-free,
  // so its column is blank until the total line.
  $("summary-table").innerHTML =
    head +
    "<tbody>" +
    row(t("ui.row_excl"), s.spot.exVat, null) +
    row(t("ui.row_vat_rate", { rate: pct(report.vatRate) }), s.spot.vat, null) +
    row(t("ui.row_total"), s.spot.inclVat, s.fixed?.total) +
    "</tbody>";
}

function renderDetail(report) {
  const cur = report.currency;
  const hasFixed = report.fixedPrice !== null && report.fixedPrice !== undefined;
  const hideEmpty = $("hide-empty").checked;
  const rows = hideEmpty
    ? report.hours.filter((h) => (h.consumption || 0) > 0)
    : report.hours;
  const columns = hasFixed ? 7 : 6;

  const head = `<thead><tr>
    <th>${t("ui.col_hour")}</th>
    <th>${t("ui.col_kwh")}</th>
    <th>${t("ui.col_unit_price", { currency: cur })}</th>
    <th>${t("ui.col_excl", { currency: cur })}</th>
    <th>${t("ui.col_vat", { currency: cur })}</th>
    <th>${t("ui.col_incl", { currency: cur })}</th>
    ${hasFixed ? `<th>${t("ui.col_fixed", { currency: cur })}</th>` : ""}
  </tr></thead>`;

  const body = rows
    .map((h) => {
      const dim = (h.consumption || 0) === 0 ? ' class="dim"' : "";
      return `<tr${dim}>
        <td>${hourLabel(h.from)}</td>
        <td>${fmt(h.consumption, 3)}</td>
        <td>${fmt(h.unitPriceInclVat, 4)}</td>
        <td>${fmt(h.spotCostExVat)}</td>
        <td>${fmt(h.spotVat)}</td>
        <td>${fmt(h.spotCostInclVat)}</td>
        ${hasFixed ? `<td>${fmt(h.fixedCost)}</td>` : ""}
      </tr>`;
    })
    .join("");

  const s = report.summary;
  const foot = `<tfoot><tr>
    <td>${hideEmpty ? t("ui.total_all") : t("ui.total")}</td>
    <td>${fmt(s.totalConsumption, 3)}</td>
    <td></td>
    <td>${fmt(s.spot.exVat)}</td>
    <td>${fmt(s.spot.vat)}</td>
    <td>${fmt(s.spot.inclVat)}</td>
    ${hasFixed ? `<td>${fmt(s.fixed.total)}</td>` : ""}
  </tr></tfoot>`;

  $("detail-table").innerHTML =
    head +
    (rows.length
      ? `<tbody>${body}</tbody>${foot}`
      : `<tbody><tr><td colspan="${columns}" class="dim">${t("ui.no_hours")}</td></tr></tbody>`);
}

function renderReport(report) {
  state.report = report;
  const home = report.home;
  const name = [home.nickname, home.address1, home.postalCode, home.city]
    .filter(Boolean)
    .join(" · ");

  $("result-title").textContent = name || t("ui.report");

  const parts = [
    `${hourLabel(report.period.from)} → ${hourLabel(report.period.to)}`,
    t("ui.sub_hours", { count: report.period.hours }),
    t("ui.sub_spot_vat", {
      rate: pct(report.vatRate),
      source: report.vatRateDerived ? t("ui.vat_from_api") : t("ui.vat_assumed"),
    }),
  ];
  if (report.fixedPrice !== null && report.fixedPrice !== undefined) {
    parts.push(
      t("ui.sub_fixed_price", {
        price: fmt(report.fixedPrice, 4),
        currency: report.currency,
      })
    );
  }
  $("result-sub").textContent = parts.join(" · ");

  renderTiles(report);
  renderSummary(report);
  renderDetail(report);

  $("warnings").innerHTML = (report.warnings || [])
    .map((w) => `<div class="note">${w}</div>`)
    .join("");

  $("result").classList.remove("hidden");
  for (const id of ["dl-pdf", "dl-csv", "dl-json"]) $(id).disabled = false;
}

/* ------------------------------------------------------------ actions -- */
async function generate(event) {
  event.preventDefault();
  clearError();
  let body;
  try {
    body = buildRequest();
  } catch (err) {
    showError(err.message);
    return;
  }

  savePrefs();
  $("loading").classList.remove("hidden");
  $("submit").disabled = true;
  try {
    const response = await postJson("/api/report", body);
    renderReport(await response.json());
  } catch (err) {
    $("result").classList.add("hidden");
    showError(err.message);
  } finally {
    $("loading").classList.add("hidden");
    $("submit").disabled = false;
  }
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

async function download(path) {
  clearError();
  let body;
  try {
    body = buildRequest();
  } catch (err) {
    showError(err.message);
    return;
  }
  try {
    const response = await postJson(path, body);
    const blob = await response.blob();
    const disposition = response.headers.get("Content-Disposition") || "";
    const match = disposition.match(/filename="([^"]+)"/);
    saveBlob(blob, match ? match[1] : "tibber-report");
  } catch (err) {
    showError(err.message);
  }
}

function downloadJson() {
  if (!state.report) return;
  saveBlob(
    new Blob([JSON.stringify(state.report, null, 2)], { type: "application/json" }),
    `${state.report.label}.json`
  );
}

function applyQuickRange(kind) {
  const now = new Date();
  let start;
  let end;
  if (kind === "yesterday") {
    end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    start = new Date(end.getTime() - 86400000);
  } else if (kind === "last7") {
    end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    start = new Date(end.getTime() - 7 * 86400000);
  } else if (kind === "thismonth") {
    start = new Date(now.getFullYear(), now.getMonth(), 1);
    end = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  } else {
    start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    end = new Date(now.getFullYear(), now.getMonth(), 1);
  }
  $("start-date").value = dateValue(start);
  $("end-date").value = dateValue(end);
}

function toggleFixed() {
  $("fixed-price").disabled = !$("fixed-enabled").checked;
}

/* -------------------------------------------------------------- boot ---- */
async function loadHomes() {
  const select = $("home");
  const token = sessionToken();
  const params = new URLSearchParams({ lang: state.locale });
  if (token) params.set("token", token);

  try {
    const response = await fetch(`/api/homes?${params}`, {
      headers: { "X-Lang": state.locale },
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `HTTP ${response.status}`);
    }
    const { homes } = await response.json();
    state.homes = homes;
    state.homesLoaded = true;
    state.homesError = null;

    select.innerHTML = homes
      .map((h) => {
        const label = [h.nickname, h.address1, h.postalCode, h.city]
          .filter(Boolean)
          .join(" · ");
        return `<option value="${h.id}">${label || h.id}</option>`;
      })
      .join("");

    // A remembered home wins over the server-side postal-code default.
    const prefs = loadPrefs();
    const remembered = homes.find((h) => h.id === prefs.homeId);
    if (remembered) {
      select.value = remembered.id;
    } else {
      const preferred = state.config?.defaultPostalCode;
      if (preferred) {
        const match = homes.find(
          (h) =>
            (h.postalCode || "").replace(/\s/g, "") === preferred.replace(/\s/g, "")
        );
        if (match) select.value = match.id;
      }
    }
    $("token-form").classList.add("hidden");
  } catch (err) {
    select.innerHTML = "";
    state.homes = [];
    state.homesError = err.message;
    $("token-form").classList.remove("hidden");
  }
  updateHomeHint();
}

function restorePrefs(prefs) {
  if (prefs.startTime) $("start-time").value = prefs.startTime;
  if (prefs.endTime) $("end-time").value = prefs.endTime;
  if (prefs.fixedEnabled) {
    $("fixed-enabled").checked = true;
    if (prefs.fixedPrice) $("fixed-price").value = prefs.fixedPrice;
  }
  if (prefs.hideEmpty) $("hide-empty").checked = true;
  toggleFixed();
}

async function init() {
  try {
    state.config = await (await fetch("/api/config")).json();
  } catch {
    state.config = {};
  }

  const prefs = loadPrefs();
  // Remembered language first, then the server default, then the browser's.
  state.locale = normalizeLocale(
    prefs.lang || state.config.defaultLanguage || navigator.language
  );
  $("lang").value = state.locale;

  // Server-side defaults only apply when nothing was remembered.
  if (
    prefs.fixedEnabled === undefined &&
    state.config.defaultFixedPrice !== null &&
    state.config.defaultFixedPrice !== undefined
  ) {
    $("fixed-enabled").checked = true;
    $("fixed-price").value = state.config.defaultFixedPrice;
  }

  restorePrefs(prefs);
  applyQuickRange("last7");
  if (prefs.startTime) $("start-time").value = prefs.startTime;
  if (prefs.endTime) $("end-time").value = prefs.endTime;

  applyLanguage();

  if (
    !state.config.tokenConfigured &&
    !sessionToken() &&
    state.config.allowTokenOverride !== false
  ) {
    $("token-form").classList.remove("hidden");
  }

  await loadHomes();
}

/* ------------------------------------------------------------- events -- */
$("form").addEventListener("submit", generate);
$("fixed-enabled").addEventListener("change", () => {
  toggleFixed();
  savePrefs();
});
$("dl-pdf").addEventListener("click", () => download("/api/report.pdf"));
$("dl-csv").addEventListener("click", () => download("/api/report.csv"));
$("dl-json").addEventListener("click", downloadJson);
$("hide-empty").addEventListener("change", () => {
  savePrefs();
  if (state.report) renderDetail(state.report);
});
$("lang").addEventListener("change", () => {
  state.locale = normalizeLocale($("lang").value);
  savePrefs();
  applyLanguage();
});
$("reset").addEventListener("click", () => {
  clearPrefs();
  location.reload();
});
for (const id of ["home", "start-time", "end-time", "fixed-price"]) {
  $(id).addEventListener("change", savePrefs);
}
for (const chip of document.querySelectorAll(".chip")) {
  chip.addEventListener("click", () => applyQuickRange(chip.dataset.range));
}
$("token-save").addEventListener("click", async () => {
  const value = $("token").value.trim();
  if (!value) return;
  setSessionToken(value);
  $("token").value = "";
  updateTokenPill();
  clearError();
  await loadHomes();
});

init();
