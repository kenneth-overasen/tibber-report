"""Runtime configuration, sourced from environment variables."""
import os

from .i18n import normalize as normalize_locale


def _float_or_none(name: str):
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


class Settings:
    def __init__(self) -> None:
        # Required for anything that talks to Tibber. Can also be supplied
        # per-request from the UI, which takes precedence over this value.
        self.token = os.getenv("TIBBER_TOKEN", "").strip()
        self.api_url = os.getenv(
            "TIBBER_API_URL", "https://api.tibber.com/v1-beta/gql"
        ).strip()
        # Pre-fills in the UI.
        self.default_postal_code = os.getenv("TIBBER_POSTAL_CODE", "").strip()
        self.default_fixed_price = _float_or_none("TIBBER_FIXED_PRICE")
        self.timezone = os.getenv("TZ", "Europe/Oslo").strip() or "Europe/Oslo"
        # Language the UI and reports start in; the UI can switch at any time.
        self.default_language = normalize_locale(os.getenv("TIBBER_LANGUAGE"))
        # Safety valve: how far back a single report may reach. The Tibber API
        # is queried with `last: <hours>` counted back from now, so a very old
        # start date means a very large response.
        self.max_lookback_hours = int(os.getenv("TIBBER_MAX_LOOKBACK_HOURS", "26280"))
        # Allow the UI to send its own token (handy for multi-account use).
        self.allow_token_override = os.getenv(
            "TIBBER_ALLOW_TOKEN_OVERRIDE", "true"
        ).strip().lower() in ("1", "true", "yes")

    def token_for(self, override: str | None) -> str:
        if override and self.allow_token_override:
            return override.strip()
        return self.token


settings = Settings()
