from api.client import RobloxApiError, request_json


USERS_BASE = "https://users.roblox.com/v1"
FRIENDS_BASE = "https://friends.roblox.com/v1"


def resolve_user_id(target: str) -> int:
    if target.isdigit():
        return int(target)

    payload = request_json(
        "POST",
        f"{USERS_BASE}/usernames/users",
        json_body={"usernames": [target], "excludeBannedUsers": False},
    )
    users = payload.get("data", [])
    exact_matches = [user for user in users if user.get("name", "").lower() == target.lower()]
    if not exact_matches:
        returned_names = ", ".join(user.get("name", "") for user in users if user.get("name"))
        detail = f" Roblox returned: {returned_names}" if returned_names else ""
        raise RobloxApiError(f"Exact username not found: {target}.{detail}")
    if not users:
        raise RobloxApiError(f"Username not found: {target}")
    return int(exact_matches[0]["id"])


def get_public_profile(user_id: int) -> dict:
    profile = request_json("GET", f"{USERS_BASE}/users/{user_id}")
    return {
        "user_id": profile.get("id", user_id),
        "username": profile.get("name"),
        "display_name": profile.get("displayName"),
        "description": profile.get("description"),
        "created": profile.get("created"),
        "is_banned": profile.get("isBanned"),
        "profile_url": f"https://www.roblox.com/users/{user_id}/profile",
    }


def get_public_counts(user_id: int) -> dict:
    return {
        "friend_count": _get_count(f"{FRIENDS_BASE}/users/{user_id}/friends/count"),
        "follower_count": _get_count(f"{FRIENDS_BASE}/users/{user_id}/followers/count"),
        "following_count": _get_count(f"{FRIENDS_BASE}/users/{user_id}/followings/count"),
    }


def _get_count(url: str) -> int | None:
    payload = request_json("GET", url)
    return payload.get("count")
