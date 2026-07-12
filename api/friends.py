from api.client import request_json


FRIENDS_BASE = "https://friends.roblox.com/v1"
USERS_BASE = "https://users.roblox.com/v1"


def get_public_friends(user_id: int) -> list[dict]:
    payload = request_json("GET", f"{FRIENDS_BASE}/users/{user_id}/friends")
    friends = [
        {
            "friend_user_id": friend.get("id"),
            "friend_username": friend.get("name"),
            "friend_display_name": friend.get("displayName"),
            "is_banned": friend.get("isBanned"),
            "profile_url": f"https://www.roblox.com/users/{friend.get('id')}/profile" if friend.get("id") else None,
        }
        for friend in payload.get("data", [])
    ]
    return _fill_missing_friend_names(friends)


def _fill_missing_friend_names(friends: list[dict]) -> list[dict]:
    missing_ids = [
        friend["friend_user_id"]
        for friend in friends
        if friend.get("friend_user_id") and (not friend.get("friend_username") or not friend.get("friend_display_name"))
    ]
    if not missing_ids:
        return friends

    users_by_id: dict[int, dict] = {}
    for start in range(0, len(missing_ids), 100):
        batch = missing_ids[start : start + 100]
        payload = request_json(
            "POST",
            f"{USERS_BASE}/users",
            json_body={"userIds": batch, "excludeBannedUsers": False},
        )
        users_by_id.update({int(user["id"]): user for user in payload.get("data", []) if user.get("id") is not None})

    for friend in friends:
        friend_user_id = friend.get("friend_user_id")
        details = users_by_id.get(int(friend_user_id)) if friend_user_id is not None else None
        if not details:
            continue
        friend["friend_username"] = friend.get("friend_username") or details.get("name")
        friend["friend_display_name"] = friend.get("friend_display_name") or details.get("displayName")
        if friend.get("is_banned") is None:
            friend["is_banned"] = details.get("isBanned")

    return friends
