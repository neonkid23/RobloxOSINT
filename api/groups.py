from api.client import request_json


GROUPS_BASE = "https://groups.roblox.com/v2"


def get_public_groups(user_id: int) -> list[dict]:
    payload = request_json("GET", f"{GROUPS_BASE}/users/{user_id}/groups/roles")
    groups = []
    for item in payload.get("data", []):
        group = item.get("group", {})
        role = item.get("role", {})
        groups.append(
            {
                "group_id": group.get("id"),
                "name": group.get("name"),
                "member_count": group.get("memberCount"),
                "role_id": role.get("id"),
                "role_name": role.get("name"),
                "role_rank": role.get("rank"),
            }
        )
    return groups

