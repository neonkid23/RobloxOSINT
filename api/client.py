import json
import logging
import time
from typing import Any

import requests

from config import (
    DEFAULT_RETRIES,
    DEFAULT_RETRY_DELAY_SECONDS,
    DEFAULT_TIMEOUT_SECONDS,
    ROBLOX_OPEN_CLOUD_API_KEY,
)


class RobloxApiError(RuntimeError):
    pass


def request_json(
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    api_key_required: bool = False,
    cookie_header: str | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> dict[str, Any]:
    """Make a Roblox API request and return JSON with retries and logging."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "roblox-public-account-lookup/1.0",
    }

    if api_key_required:
        if not ROBLOX_OPEN_CLOUD_API_KEY:
            raise RobloxApiError("This endpoint requires ROBLOX_OPEN_CLOUD_API_KEY in .env.")
        headers["x-api-key"] = ROBLOX_OPEN_CLOUD_API_KEY
    if cookie_header:
        headers["Cookie"] = cookie_header

    last_error = None
    for attempt in range(1, retries + 1):
        started = time.time()
        response = None
        try:
            response = requests.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=headers,
                timeout=timeout,
            )
            elapsed_ms = int((time.time() - started) * 1000)
            logging.info(
                "%s %s status=%s elapsed_ms=%s params=%s",
                method.upper(),
                response.url,
                response.status_code,
                elapsed_ms,
                json.dumps(params or {}),
            )

            if response.status_code == 429:
                last_error = f"HTTP 429 rate limited at {response.url}"
                wait_seconds = _retry_after_seconds(response, retry_delay * attempt)
                logging.warning("Rate limited by Roblox API. Waiting %.1f seconds.", wait_seconds)
                time.sleep(wait_seconds)
                continue

            if 500 <= response.status_code < 600 and attempt < retries:
                last_error = f"HTTP {response.status_code} from {response.url}"
                time.sleep(retry_delay * attempt)
                continue

            if response.status_code in (401, 403):
                raise RobloxApiError(
                    f"Roblox API returned {response.status_code} for {response.url}: access is not allowed for this public lookup."
                )

            response.raise_for_status()

            if not response.content:
                return {}
            return json.loads(response.content.decode("utf-8"))

        except requests.Timeout as exc:
            last_error = f"timeout calling {url}"
            logging.warning("Timeout calling %s attempt=%s", url, attempt)
            if attempt >= retries:
                raise RobloxApiError(f"Timed out calling Roblox API: {url}") from exc
            time.sleep(retry_delay * attempt)
        except requests.RequestException as exc:
            status = response.status_code if response is not None else "no_response"
            request_url = response.url if response is not None else url
            last_error = f"{request_url} status={status} error={exc}"
            logging.error("%s %s failed status=%s error=%s", method.upper(), url, status, exc)
            if attempt >= retries:
                raise RobloxApiError(f"Roblox API request failed: {request_url} ({exc})") from exc
            time.sleep(retry_delay * attempt)
        except ValueError as exc:
            raise RobloxApiError(f"Roblox API returned invalid JSON: {url}") from exc

    detail = f" Last error: {last_error}" if last_error else ""
    raise RobloxApiError(f"Roblox API request failed after retries: {method.upper()} {url}.{detail}")


def paginate(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data_key: str = "data",
    max_pages: int | None = None,
    cookie_header: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor = None
    pages_read = 0

    while True:
        page_params = dict(params or {})
        if cursor:
            page_params["cursor"] = cursor

        payload = request_json("GET", url, params=page_params, cookie_header=cookie_header)
        results.extend(payload.get(data_key, []))

        pages_read += 1
        if max_pages is not None and pages_read >= max_pages:
            break

        cursor = payload.get("nextPageCursor")
        if not cursor:
            break

    return results


def _retry_after_seconds(response: requests.Response, fallback: float) -> float:
    retry_after = response.headers.get("Retry-After")
    if not retry_after:
        return fallback
    try:
        return max(float(retry_after), fallback)
    except ValueError:
        return fallback
