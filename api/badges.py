import logging

from config import DEFAULT_PAGE_LIMIT
from api.client import RobloxApiError
from api.client import paginate


BADGES_BASE = "https://badges.roblox.com/v1"
INVENTORY_BADGES_PAGE = "https://www.roblox.com/users/{user_id}/inventory/#!/badges"


def get_public_badges(user_id: int, max_pages: int | None = None, cookie_header: str | None = None) -> list[dict]:
    badges = _get_badges_with_fallbacks(user_id, max_pages=max_pages, cookie_header=cookie_header)
    return [
        {
            "badge_id": badge.get("id"),
            "name": badge.get("name"),
            "description": badge.get("description"),
            "display_icon_image_id": badge.get("displayIconImageId"),
            "created": badge.get("created"),
            "updated": badge.get("updated"),
            "inventory_badges_url": INVENTORY_BADGES_PAGE.format(user_id=user_id),
            "source": "Roblox inventory badges page API",
        }
        for badge in badges
    ]


def _get_badges_with_fallbacks(
    user_id: int,
    max_pages: int | None = None,
    cookie_header: str | None = None,
) -> list[dict]:
    attempts = [
        {"limit": DEFAULT_PAGE_LIMIT, "sortOrder": "Desc"},
        {"limit": min(DEFAULT_PAGE_LIMIT, 100), "sortOrder": "Asc"},
        {"limit": 10, "sortOrder": "Desc"},
        {"limit": 10, "sortOrder": "Asc"},
    ]
    last_error = None
    for params in attempts:
        try:
            return paginate(
                f"{BADGES_BASE}/users/{user_id}/badges",
                params=params,
                max_pages=max_pages,
                cookie_header=cookie_header,
            )
        except RobloxApiError as exc:
            last_error = exc
            logging.info("Badge lookup attempt failed for user_id=%s params=%s: %s", user_id, params, exc)

    raise RobloxApiError(f"Public badges are unavailable after fallback attempts. Last error: {last_error}")
