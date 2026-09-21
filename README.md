# Tibber consumption report

A small web tool that pulls hourly power consumption and costs from the
[Tibber GraphQL API](https://developer.tibber.com/docs/reference), shows a
summary plus hour-by-hour detail for any period you pick, and lets you download
the result as a PDF receipt, CSV or JSON.

It also accepts a **fixed price per kWh** that overrides Tibber's spot price, so
you can see what the same consumption would have cost on a fixed contract and
what the difference is.

The interface and the reports are available in **English and Norwegian**, and
the browser remembers your home, fixed price and language between visits.

## Quick start

```bash
cp .env.example .env    # then put your token in TIBBER_TOKEN
docker compose up --build
```

Open <http://localhost:8000>.

Get a personal access token at
<https://developer.tibber.com/settings/access-token>.

### Without compose

```bash
docker build -t tibber-report .
docker run --rm -p 8000:8000 -e TIBBER_TOKEN=your-token tibber-report
```

### Running on a different machine than you build on

`exec /usr/local/bin/uvicorn: exec format error` in the container logs means the
image was built for a different CPU architecture than the host. Some
dependencies (pydantic-core, reportlab, uvloop) ship compiled wheels, so an
image only runs on the architecture it was built for. An Apple Silicon Mac
produces **arm64**; most servers, NAS boxes and VPS instances are **amd64**.

Confirm the mismatch:

```bash
docker image inspect tibber-report:latest --format 'image: {{.Architecture}}' ; docker version --format 'host:  {{.Server.Arch}}'
```

The simplest fix is to build on the machine that will run it — clone the repo
there and `docker compose up --build`. To cross-build from a Mac instead:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose build
```

Or, without compose:

```bash
docker buildx build --platform linux/amd64 -t tibber-report:latest --load .
```

To move that image to the target host without a registry:

```bash
docker save tibber-report:latest | ssh user@host 'docker load'
```

If the diagnostic shows the opposite — an **amd64 image on an arm64 host**,
i.e. you are running it on the Mac itself — then something is forcing the
platform. Check `echo $DOCKER_DEFAULT_PLATFORM` and any `platform:` line in
`docker-compose.yml`; unset it and rebuild, or enable **Use Rosetta for x86/amd64
emulation** in Docker Desktop → Settings → General.

Swap `linux/amd64` for `linux/arm64` when the target is a Raspberry Pi or an
ARM server. To build one image that runs on both, push to a registry:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t youruser/tibber-report:latest --push .
```

### Without Docker

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
TIBBER_TOKEN=your-token .venv/bin/uvicorn app.main:app --port 8000
```

## Configuration

Everything is an environment variable; only `TIBBER_TOKEN` is required.

| Variable | Default | Purpose |
| --- | --- | --- |
| `TIBBER_TOKEN` | — | **Required.** Tibber personal access token. |
| `TIBBER_API_URL` | `https://api.tibber.com/v1-beta/gql` | GraphQL endpoint. |
| `TZ` | `Europe/Oslo` | Fallback time zone when a home reports none. |
| `TIBBER_LANGUAGE` | `en` | Starting language: `en` or `nb`. |
| `TIBBER_POSTAL_CODE` | — | Pre-selects this home in the UI. |
| `TIBBER_FIXED_PRICE` | — | Pre-fills the fixed-price override, per kWh. |
| `TIBBER_ALLOW_TOKEN_OVERRIDE` | `true` | Set `false` to forbid entering a token in the UI. |
| `TIBBER_MAX_LOOKBACK_HOURS` | `26280` (3 years) | Guard against enormous queries. |

If no token is set in the environment, the UI offers a field to paste one. That
token is kept in the browser's `sessionStorage` and sent with each request — it
is never written to disk on the server.

## Using it

1. Pick a **home**. The dropdown is filled from your Tibber account; homes are
   labelled with nickname, street, postal code and city.
2. Pick a **period**. The end is exclusive, so `2026-08-13 13:00` →
   `2026-08-16 18:00` covers the hour starting 13:00 through the hour starting
   17:00. The quick-range chips fill in common periods.
3. Optionally tick **Use a fixed price per kWh** and enter your contract price.
   It is used exactly as entered — VAT does not apply to a fixed price.
4. **Generate report**, then download PDF / CSV / JSON.

### Language

The picker in the top bar switches between **English** and **Norsk** (Bokmål).
It changes the interface, the report on screen, the downloaded PDF and CSV, and
every warning and error message. Numbers follow the language too: Norwegian
uses a comma for decimals, so a CSV opened in a Norwegian Excel reads correctly
without a conversion step.

`TIBBER_LANGUAGE` sets the starting language. A browser that has not chosen one
falls back to that, then to the browser's own `Accept-Language`.

Scripted callers can pass `"lang": "nb"` in the request body, or send an
`X-Lang: nb` header; `Accept-Language` is honoured as a last resort.

### Remembered settings

The selected home, fixed price, start/end times, the
"hide empty hours" toggle and the language are saved in the browser's
`localStorage`, so they come back on the next visit. **Reset saved settings**
clears them and returns to the server-side defaults.

Dates are deliberately *not* remembered — a report is almost always for a new
period, so the range resets to the last 7 days. The API token is kept in
`sessionStorage` instead, so it is dropped when the tab closes.

## How the numbers are calculated

Tibber returns, per hour:

| Field | Meaning |
| --- | --- |
| `consumption` | kWh consumed |
| `unitPrice` | price per kWh **including VAT** |
| `unitPriceVAT` | the VAT share *contained in* `unitPrice` |
| `cost` | `consumption × unitPrice`, **including VAT** |

So the tool computes:

```
unit price excl. VAT = unitPrice − unitPriceVAT
cost incl. VAT       = cost            (falls back to consumption × unitPrice)
VAT                  = consumption × unitPriceVAT
cost excl. VAT       = cost incl. VAT − VAT
```

> **Note:** `cost` already contains VAT. Adding `unitPriceVAT × consumption` on
> top of it — as the old script in `legacy/` does — double-counts VAT and inflates
> the total by the VAT rate.

The **VAT rate** is derived from the period's own data
(`Σ unitPriceVAT / Σ (unitPrice − unitPriceVAT)`), so VAT-exempt regions
(Nordland, Troms and Finnmark) come out at 0 % without any configuration. It
falls back to 25 % only when the data gives no signal, and you can always
override it in the UI.

A **fixed price** replaces the unit price but not the consumption. VAT does not
apply to it, so there is nothing to add or split out:

```
fixed total = consumption × fixed price
difference  = fixed total − spot total incl. VAT  (positive ⇒ fixed costs more)
```

The difference is measured against the spot total *including* VAT, since that is
what the spot contract actually costs.

Prices cover **energy only** — grid rent, fixed monthly fees and production
rewards are not part of the Tibber `cost` field and are not in the report.

## HTTP API

The UI is a thin layer over a JSON API you can script against.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Liveness probe. |
| `GET /api/config` | Non-secret defaults for the UI. |
| `GET /api/homes` | Homes on the account. |
| `POST /api/report` | The report as JSON. |
| `POST /api/report.csv` | The report as a semicolon-separated CSV (Excel-friendly, UTF-8 BOM). |
| `POST /api/report.pdf` | The report as a PDF receipt. |
| `GET /logo.png` | The bundled Tibber mark (also at `/favicon.ico` and `/static/tibber-logo.png`), cached for a day. |

All three `report` endpoints take the same body:

```jsonc
{
  "home_id": "…",                 // or "postal_code": "1747"
  "start": "2026-08-13T13:00",    // local wall clock
  "end": "2026-08-16T18:00",      // exclusive
  "fixed_price": 1.25,            // optional; per kWh, VAT does not apply
  "timezone": "Europe/Oslo",      // optional; default is the home's own zone
  "token": "…",                   // optional; overrides TIBBER_TOKEN
  "lang": "nb"                    // optional; 'en' or 'nb'
}
```

```bash
curl -X POST http://localhost:8000/api/report.pdf \
  -H 'Content-Type: application/json' \
  -d '{"postal_code":"1747","start":"2026-08-13T13:00","end":"2026-08-16T18:00","fixed_price":1.25}' \
  -o report.pdf
```

Interactive docs are at `/docs`.

## Data availability

Tibber only returns hours its meter reading covers. Hours before the
subscription started, and the most recent hour or two, are usually missing. The
report says how many hours it actually got and lists the gaps as notes rather
than silently treating them as zero-cost.

Because the API is queried as "the last *N* hours" counted back from now, a
report that starts a long time ago means a large response. `TIBBER_MAX_LOOKBACK_HOURS`
caps that.

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

The tests cover the VAT arithmetic, fixed-price costing, period filtering,
timestamp parsing and both export formats — no network access needed.

They also guard the translations: both locales must define the same keys with
the same `{placeholders}`, no Norwegian string may be left as its English
original, and every `data-i18n` attribute in the HTML must resolve to a real
key. Adding a string in one language and forgetting the other fails the suite.

## Layout

```
app/
  main.py        FastAPI routes
  tibber.py      GraphQL client
  report.py      filtering + all cost arithmetic
  exporters.py   CSV and PDF
  i18n.py        translations for reports, warnings and errors
  config.py      environment variables
  static/
    index.html       markup, with data-i18n hooks
    app.js           UI logic, persistence
    i18n.js          UI translations
    styles.css
    tibber-logo.png  bundled Tibber mark (Tibber's trademark)
tests/           unit tests
legacy/          the original CLI script, kept for reference
  main.py          the script itself
  requirements.txt its own dependencies, separate from the root ones
```
