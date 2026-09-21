"""FastAPI application: JSON API + static single-page UI."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import settings
from .exporters import to_csv, to_pdf
from .i18n import LOCALES, LocalizedError
from .i18n import normalize as normalize_locale
from .report import (
    FixedPrice,
    Report,
    ReportError,
    build_report,
    get_zone,
    hours_back_from_now,
    parse_local,
)
from .tibber import TibberClient, TibberError


class ApiError(LocalizedError):
    """A request-level error, rendered in the caller's language."""


log = logging.getLogger("tibber-tool")

STATIC_DIR = Path(__file__).parent / "static"
LOGO_PATH = STATIC_DIR / "tibber-logo.png"

app = FastAPI(
    title="Tibber consumption report",
    description="Fetch hourly power consumption and costs from the Tibber API.",
    version="1.0.0",
)


# --------------------------------------------------------------- models ---
class ReportRequest(BaseModel):
    home_id: str | None = Field(
        default=None, description="Tibber home id. Takes precedence over postal_code."
    )
    postal_code: str | None = Field(
        default=None, description="Select the home by postal code instead of id."
    )
    start: str = Field(description="Local start, YYYY-MM-DD or YYYY-MM-DDTHH:MM")
    end: str = Field(description="Local end (exclusive), same format as start")
    fixed_price: float | None = Field(
        default=None,
        description="Override price per kWh, VAT-free. Omit to use spot only.",
    )
    fixed_only: bool = Field(
        default=False,
        description="Report the fixed price alone, without the spot "
        "comparison. Ignored unless fixed_price is given.",
    )
    timezone: str | None = Field(
        default=None, description="IANA zone. Defaults to the home's own time zone."
    )
    token: str | None = Field(default=None, description="Per-request API token.")
    lang: str | None = Field(
        default=None,
        description="Language for report labels and messages: 'en' or 'nb'. "
        "Defaults to the X-Lang header, then TIBBER_LANGUAGE.",
    )


# ------------------------------------------------------------- helpers ----
def locale_from_request(request: Request) -> str:
    """The caller's language: explicit header, then query, then Accept-Language."""
    explicit = request.headers.get("x-lang") or request.query_params.get("lang")
    if explicit:
        return normalize_locale(explicit)
    header = request.headers.get("accept-language")
    if header:
        return normalize_locale(header)
    return settings.default_language


def _client(token_override: str | None) -> TibberClient:
    return TibberClient(settings.token_for(token_override), settings.api_url)


async def _resolve_home(client: TibberClient, req: ReportRequest) -> dict:
    """Pick the home to report on, by id or postal code."""
    homes = await client.list_homes()
    if not homes:
        raise ApiError("err.no_homes", status_code=404)

    if req.home_id:
        for home in homes:
            if home["id"] == req.home_id:
                return home
        raise ApiError("err.home_not_found", status_code=404, home_id=req.home_id)

    if req.postal_code:
        wanted = req.postal_code.replace(" ", "").strip()
        matches = [
            h
            for h in homes
            if (h.get("postalCode") or "").replace(" ", "").strip() == wanted
        ]
        if not matches:
            available = ", ".join(
                sorted({h.get("postalCode") or "?" for h in homes})
            )
            raise ApiError(
                "err.postal_not_found",
                status_code=404,
                postal_code=req.postal_code,
                available=available,
            )
        if len(matches) > 1:
            raise ApiError(
                "err.postal_ambiguous",
                status_code=409,
                count=len(matches),
                postal_code=req.postal_code,
            )
        return matches[0]

    if len(homes) == 1:
        return homes[0]
    raise ApiError("err.select_home", status_code=400)


def _locale(req: ReportRequest, request: Request) -> str:
    if req.lang:
        return normalize_locale(req.lang)
    return locale_from_request(request)


async def _build(req: ReportRequest) -> Report:
    client = _client(req.token)
    home = await _resolve_home(client, req)

    zone_name = req.timezone or home.get("timeZone") or settings.timezone
    zone = get_zone(zone_name)

    start = parse_local(req.start, zone)
    end = parse_local(req.end, zone)
    if end <= start:
        raise ApiError("err.end_before_start")

    now = datetime.now(tz=zone)
    if start > now:
        raise ApiError("err.future_start")

    hours = hours_back_from_now(start, now)
    if hours > settings.max_lookback_hours:
        raise ApiError(
            "err.lookback",
            hours=hours,
            limit=settings.max_lookback_hours,
        )

    payload = await client.consumption(home["id"], hours)

    fixed = None
    if req.fixed_price is not None:
        if req.fixed_price < 0:
            raise ApiError("err.negative_price")
        fixed = FixedPrice(price=req.fixed_price)

    merged_home = {**home, **{k: v for k, v in payload["home"].items() if v}}

    return build_report(
        home=merged_home,
        nodes=payload["nodes"],
        start=start,
        end=end,
        zone=zone,
        fixed_price=fixed,
        fixed_only=req.fixed_only,
        currency_fallback=(payload["pageInfo"] or {}).get("currency")
        or home.get("currency")
        or "NOK",
    )


# -------------------------------------------------------------- routes ----
def _localized_response(request: Request, exc: LocalizedError) -> JSONResponse:
    locale = locale_from_request(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.localized(locale), "code": exc.code},
    )


@app.exception_handler(TibberError)
async def _tibber_error_handler(request: Request, exc: TibberError):
    return _localized_response(request, exc)


@app.exception_handler(ReportError)
async def _report_error_handler(request: Request, exc: ReportError):
    return _localized_response(request, exc)


@app.exception_handler(ApiError)
async def _api_error_handler(request: Request, exc: ApiError):
    return _localized_response(request, exc)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/api/config")
async def get_config() -> dict:
    """Non-secret defaults so the UI can pre-fill itself."""
    return {
        "languages": list(LOCALES),
        "defaultLanguage": settings.default_language,
        "tokenConfigured": bool(settings.token),
        "allowTokenOverride": settings.allow_token_override,
        "defaultPostalCode": settings.default_postal_code,
        "defaultFixedPrice": settings.default_fixed_price,
        "timezone": settings.timezone,
    }


@app.get("/api/homes")
async def get_homes(token: str | None = None) -> dict:
    return {"homes": await _client(token).list_homes()}


@app.post("/api/report")
async def post_report(req: ReportRequest, request: Request) -> dict:
    locale = _locale(req, request)
    return (await _build(req)).as_dict(locale)


@app.post("/api/report.csv")
async def post_report_csv(req: ReportRequest, request: Request) -> Response:
    locale = _locale(req, request)
    report = await _build(req)
    # UTF-8 BOM so Excel picks the encoding up.
    body = ("﻿" + to_csv(report, locale)).encode("utf-8")
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{report.label()}.csv"'
        },
    )


@app.post("/api/report.pdf")
async def post_report_pdf(req: ReportRequest, request: Request) -> Response:
    locale = _locale(req, request)
    report = await _build(req)
    return Response(
        content=to_pdf(report, locale),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{report.label()}.pdf"'
        },
    )


@app.get("/logo.png", include_in_schema=False)
async def logo() -> FileResponse:
    """The bundled Tibber mark, on a stable path for outside callers."""
    return FileResponse(
        LOGO_PATH,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    # Browsers ask for this whether or not the page declares an icon link.
    return FileResponse(
        LOGO_PATH,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
