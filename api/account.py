from typing import Any

from api.client import request_json


USERS_BASE = "https://users.roblox.com/v1"


def get_authenticated_account_info(cookie_header: str) -> dict[str, Any]:
    authenticated = request_json("GET", f"{USERS_BASE}/users/authenticated", cookie_header=cookie_header)
    age_bracket = request_json("GET", f"{USERS_BASE}/users/authenticated/age-bracket", cookie_header=cookie_header)
    birthdate = request_json("GET", f"{USERS_BASE}/birthdate", cookie_header=cookie_header)
    return {
        "authenticated_user_id": authenticated.get("id"),
        "authenticated_username": authenticated.get("name"),
        "authenticated_display_name": authenticated.get("displayName"),
        "age_bracket": age_bracket.get("ageBracket"),
        "birthdate": {
            "birth_month": birthdate.get("birthMonth"),
            "birth_day": birthdate.get("birthDay"),
            "birth_year": birthdate.get("birthYear"),
        },
        "source": "Roblox authenticated account endpoints",
    }
