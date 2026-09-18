"""Thin client for the Tibber GraphQL API.

Schema reference: https://developer.tibber.com/docs/reference

Relevant facts about the `Consumption` node, taken from the schema's own
descriptions:

  * ``consumption``   -- kWh consumed in the interval.
  * ``unitPrice``     -- price per kWh *including* VAT.
  * ``unitPriceVAT``  -- the VAT portion *of* ``unitPrice`` (not an addition).
  * ``cost``          -- consumption x unitPrice, including VAT, excluding
                         grid fees and production rewards.
"""
from __future__ import annotations

import httpx

from .i18n import LocalizedError

HOMES_QUERY = """
query Homes {
  viewer {
    name
    homes {
      id
      appNickname
      timeZone
      address {
        address1
        postalCode
        city
        country
      }
      currentSubscription {
        priceInfo {
          current {
            currency
          }
        }
      }
    }
  }
}
"""

CONSUMPTION_QUERY = """
query Consumption($homeId: ID!, $hours: Int!) {
  viewer {
    home(id: $homeId) {
      id
      appNickname
      timeZone
      address {
        address1
        postalCode
        city
        country
      }
      consumption(resolution: HOURLY, last: $hours, filterEmptyNodes: false) {
        pageInfo {
          count
          currency
          totalCost
          totalConsumption
        }
        nodes {
          from
          to
          unitPrice
          unitPriceVAT
          consumption
          consumptionUnit
          cost
          currency
        }
      }
    }
  }
}
"""


class TibberError(LocalizedError, RuntimeError):
    """Raised when the Tibber API rejects a request or returns GraphQL errors."""


class TibberClient:
    def __init__(self, token: str, api_url: str, timeout: float = 60.0):
        if not token:
            raise TibberError("err.no_token", status_code=400)
        self._token = token
        self._api_url = api_url
        self._timeout = timeout

    async def _execute(self, query: str, variables: dict | None = None) -> dict:
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    self._api_url,
                    headers={
                        "Authorization": f"Bearer {self._token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.HTTPError as exc:
                raise TibberError(
                    "err.unreachable", status_code=502, error=str(exc)
                ) from exc

        if response.status_code in (401, 403):
            raise TibberError("err.token_rejected", status_code=401)
        if response.status_code == 429:
            raise TibberError("err.rate_limited", status_code=429)
        if response.status_code >= 400:
            raise TibberError(
                "err.http_status",
                status_code=502,
                status=response.status_code,
                body=response.text[:300],
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise TibberError("err.non_json", status_code=502) from exc

        if body.get("errors"):
            messages = "; ".join(
                e.get("message", "unknown error") for e in body["errors"]
            )
            codes = {
                (e.get("extensions") or {}).get("code") for e in body["errors"]
            }
            if "UNAUTHENTICATED" in codes:
                raise TibberError("err.token_rejected", status_code=401)
            raise TibberError("err.graphql", status_code=502, messages=messages)

        data = body.get("data")
        if data is None:
            raise TibberError("err.no_data_returned", status_code=502)
        return data

    async def list_homes(self) -> list[dict]:
        data = await self._execute(HOMES_QUERY)
        viewer = data.get("viewer") or {}
        homes = viewer.get("homes") or []
        result = []
        for home in homes:
            address = home.get("address") or {}
            subscription = home.get("currentSubscription") or {}
            price_info = (subscription.get("priceInfo") or {}).get("current") or {}
            result.append(
                {
                    "id": home.get("id"),
                    "nickname": home.get("appNickname"),
                    "timeZone": home.get("timeZone"),
                    "address1": address.get("address1"),
                    "postalCode": address.get("postalCode"),
                    "city": address.get("city"),
                    "country": address.get("country"),
                    "currency": price_info.get("currency"),
                }
            )
        return result

    async def consumption(self, home_id: str, hours: int) -> dict:
        """Fetch the last `hours` hourly consumption nodes for one home."""
        data = await self._execute(
            CONSUMPTION_QUERY, {"homeId": home_id, "hours": hours}
        )
        home = (data.get("viewer") or {}).get("home")
        if not home:
            raise TibberError(
                "err.home_not_found", status_code=404, home_id=home_id
            )
        consumption = home.get("consumption") or {}
        address = home.get("address") or {}
        return {
            "home": {
                "id": home.get("id"),
                "nickname": home.get("appNickname"),
                "timeZone": home.get("timeZone"),
                "address1": address.get("address1"),
                "postalCode": address.get("postalCode"),
                "city": address.get("city"),
                "country": address.get("country"),
            },
            "pageInfo": consumption.get("pageInfo") or {},
            "nodes": consumption.get("nodes") or [],
        }
