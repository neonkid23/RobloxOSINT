import logging
import time
from typing import Any

import requests

from api.client import RobloxApiError
from config import DEFAULT_RETRIES, DEFAULT_RETRY_DELAY_SECONDS, DEFAULT_TIMEOUT_SECONDS


BLOXFLIP_LOOKUP_URL = "https://api.bloxflip.com/user/lookup/{user_id}"
RBXFLIP_WAGER_URL = "https://api.rbxflip.com/wagers/users/{user_id}/history"


def get_public_gambling_info(user_id: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        records.extend(get_rbxflip_records(user_id))
    except RobloxApiError as exc:
        logging.info("RBXFlip lookup unavailable for user_id=%s: %s", user_id, exc)

    try:
        bloxflip = get_bloxflip_record(user_id)
    except RobloxApiError as exc:
        logging.info("BloxFlip lookup unavailable for user_id=%s: %s", user_id, exc)
        bloxflip = None

    if bloxflip:
        records.append(bloxflip)
    return records


def get_rbxflip_records(user_id: int) -> list[dict[str, Any]]:
    records = []
    game_kinds = {
        "money_profit": 0,
        "robux_profit": 1,
    }

    for metric, game_kind in game_kinds.items():
        payload = request_external_json(
            RBXFLIP_WAGER_URL.format(user_id=user_id),
            params={"page": 0, "gameKind": game_kind},
            source="RBXFlip",
        )
        metadata = payload.get("metadata") or {}
        total_profit = metadata.get("totalProfit")
        if total_profit in (None, 0):
            continue
        records.append(
            {
                "source": "rbxflip",
                "metric": metric,
                "game_kind": game_kind,
                "total_profit": total_profit,
                "metadata": metadata,
            }
        )

    return records


def get_bloxflip_record(user_id: int) -> dict[str, Any] | None:
    payload = request_external_json(
        BLOXFLIP_LOOKUP_URL.format(user_id=user_id),
        source="BloxFlip",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        },
    )
    if not payload.get("success"):
        return None

    data = {key: value for key, value in payload.items() if key not in {"success", "username"}}
    if not data:
        return None
    return {
        "source": "bloxflip",
        "username": payload.get("username"),
        "data": data,
    }


def request_external_json(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    source: str,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "roblox-public-account-lookup/1.0",
    }
    request_headers.update(headers or {})

    last_error = None
    for attempt in range(1, DEFAULT_RETRIES + 1):
        response = None
        started = time.time()
        try:
            response = requests.get(
                url,
                params=params,
                headers=request_headers,
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
            elapsed_ms = int((time.time() - started) * 1000)
            logging.info(
                "GET %s status=%s elapsed_ms=%s params=%s source=%s",
                response.url,
                response.status_code,
                elapsed_ms,
                params or {},
                source,
            )
            if response.status_code in {404, 401, 403}:
                return {}
            if response.status_code == 429 or 500 <= response.status_code < 600:
                last_error = f"HTTP {response.status_code} from {response.url}"
                if attempt < DEFAULT_RETRIES:
                    time.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
                    continue
            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
        except requests.Timeout as exc:
            last_error = f"timeout calling {url}"
            if attempt >= DEFAULT_RETRIES:
                raise RobloxApiError(f"{source} request timed out: {url}") from exc
            time.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        except requests.RequestException as exc:
            request_url = response.url if response is not None else url
            last_error = f"{request_url} error={exc}"
            if attempt >= DEFAULT_RETRIES:
                raise RobloxApiError(f"{source} request failed: {request_url} ({exc})") from exc
            time.sleep(DEFAULT_RETRY_DELAY_SECONDS * attempt)
        except ValueError as exc:
            raise RobloxApiError(f"{source} returned invalid JSON: {url}") from exc

    raise RobloxApiError(f"{source} request failed after retries. Last error: {last_error}")
