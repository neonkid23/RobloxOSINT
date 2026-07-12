import json
from pathlib import Path

from api.client import RobloxApiError


COOKIE_NAME = ".ROBLOSECURITY"
PLACEHOLDER = "PASTE_YOUR_OWN_COOKIE_VALUE_HERE"


def load_roblox_cookie_header(path: Path) -> str:
    if not path.exists():
        raise RobloxApiError(f"Cookie mode requested, but cookie file was not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    active_lines = [line for line in lines if not line.startswith("#")]
    cookie_value = _parse_json_cookie_export(text)
    for line in active_lines:
        if cookie_value:
            break
        parsed = _parse_cookie_line(line)
        if parsed:
            cookie_value = parsed
            break
    if not cookie_value:
        cookie_value = _parse_commented_cookie_line(lines)

    if not cookie_value or cookie_value == PLACEHOLDER:
        if text.strip() and not active_lines:
            raise RobloxApiError(
                f"Cookie mode requested, but {path} only contains comments. Add an active {COOKIE_NAME}=... line."
            )
        raise RobloxApiError(f"Cookie mode requested, but {COOKIE_NAME} was not found in {path}")

    return f"{COOKIE_NAME}={cookie_value}"


def _parse_cookie_line(line: str) -> str | None:
    if line.startswith(f"{COOKIE_NAME}="):
        return line.split("=", 1)[1].strip()
    if line.lower().startswith("cookie:"):
        return _extract_cookie_from_header(line.split(":", 1)[1])
    if COOKIE_NAME in line and "=" in line and ";" in line:
        return _extract_cookie_from_header(line)

    parts = line.split("\t")
    if len(parts) >= 7 and parts[5] == COOKIE_NAME:
        return parts[6].strip()
    return None


def _parse_json_cookie_export(text: str) -> str | None:
    stripped = text.strip()
    json_start = stripped.find("[")
    if json_start == -1:
        json_start = stripped.find("{")
    if json_start == -1:
        return None

    try:
        data = json.loads(stripped[json_start:])
    except json.JSONDecodeError:
        return None

    cookies = data if isinstance(data, list) else [data]
    for cookie in cookies:
        if not isinstance(cookie, dict):
            continue
        if cookie.get("name") == COOKIE_NAME and cookie.get("value"):
            return str(cookie["value"]).strip()
    return None


def _parse_commented_cookie_line(lines: list[str]) -> str | None:
    for line in lines:
        if not line.startswith("#"):
            continue
        parsed = _parse_cookie_line(line.lstrip("#").strip())
        if parsed and parsed != PLACEHOLDER:
            return parsed
    return None


def _extract_cookie_from_header(header_value: str) -> str | None:
    for cookie in header_value.split(";"):
        name, _, value = cookie.strip().partition("=")
        if name == COOKIE_NAME and value:
            return value.strip()
    return None
