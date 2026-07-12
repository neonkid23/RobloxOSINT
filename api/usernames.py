from typing import Any

from api.client import paginate


USERS_BASE = "https://users.roblox.com/v1"


def get_previous_usernames(user_id: int, max_pages: int | None = None) -> list[dict[str, Any]]:
    names = paginate(
        f"{USERS_BASE}/users/{user_id}/username-history",
        params={"limit": 100, "sortOrder": "Desc"},
        max_pages=max_pages,
    )
    return [
        {
            "previous_username": item.get("name"),
        }
        for item in names
        if item.get("name")
    ]
