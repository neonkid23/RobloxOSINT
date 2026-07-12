import logging

from config import DEFAULT_PAGE_LIMIT
from api.client import RobloxApiError, paginate


INVENTORY_BASE = "https://inventory.roblox.com/v1"


def get_public_collectibles(user_id: int, max_pages: int | None = None) -> dict:
    try:
        items = paginate(
            f"{INVENTORY_BASE}/users/{user_id}/assets/collectibles",
            params={"limit": DEFAULT_PAGE_LIMIT, "sortOrder": "Desc"},
            max_pages=max_pages,
        )
    except RobloxApiError as exc:
        logging.info("Public collectible inventory unavailable for user_id=%s: %s", user_id, exc)
        return {
            "visible": False,
            "reason": "Public collectible inventory is unavailable or hidden.",
            "items": [],
        }

    return {
        "visible": True,
        "reason": None,
        "items": [
            {
                "asset_id": item.get("assetId"),
                "name": item.get("name"),
                "asset_type": item.get("assetType"),
                "recent_average_price": item.get("recentAveragePrice"),
                "serial_number": item.get("serialNumber"),
            }
            for item in items
        ],
    }

