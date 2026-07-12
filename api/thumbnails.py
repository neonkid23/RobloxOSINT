from api.client import request_json


THUMBNAILS_BASE = "https://thumbnails.roblox.com/v1"


def get_avatar_thumbnail(user_id: int) -> str | None:
    payload = request_json(
        "GET",
        f"{THUMBNAILS_BASE}/users/avatar-headshot",
        params={"userIds": str(user_id), "size": "150x150", "format": "Png", "isCircular": "false"},
    )
    data = payload.get("data", [])
    if not data:
        return None
    return data[0].get("imageUrl")

