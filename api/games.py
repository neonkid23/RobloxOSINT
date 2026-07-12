from typing import Any

from api.client import paginate


GAMES_BASE = "https://games.roblox.com/v2"


def get_public_user_games(user_id: int, max_pages: int | None = None) -> list[dict[str, Any]]:
    games = paginate(
        f"{GAMES_BASE}/users/{user_id}/games",
        params={"accessFilter": "Public", "limit": 50, "sortOrder": "Desc"},
        max_pages=max_pages,
    )
    return [
        {
            "game_id": game.get("id"),
            "name": game.get("name"),
            "description": game.get("description"),
            "creator_id": (game.get("creator") or {}).get("id"),
            "creator_type": (game.get("creator") or {}).get("type"),
            "root_place_id": (game.get("rootPlace") or {}).get("id"),
            "created": game.get("created"),
            "updated": game.get("updated"),
            "place_visits": game.get("placeVisits"),
            "url": f"https://www.roblox.com/games/{(game.get('rootPlace') or {}).get('id')}" if (game.get("rootPlace") or {}).get("id") else None,
        }
        for game in games
    ]
