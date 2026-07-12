from typing import Any


COMMON_FIRST_NAMES = {
    "aaron", "abby", "abigail", "adam", "alex", "alexander", "alexis", "alice", "alyssa", "amanda",
    "amber", "amelia", "amy", "andrew", "angel", "anna", "anthony", "ashley", "austin", "ava",
    "bella", "ben", "benjamin", "brandon", "brian", "brianna", "brooke", "cameron", "carter",
    "charles", "charlie", "chloe", "chris", "christian", "christopher", "claire", "connor",
    "daniel", "david", "dylan", "edward", "elijah", "ella", "emily", "emma", "ethan", "eva",
    "evelyn", "gabriel", "grace", "hannah", "henry", "isabella", "jack", "jackson", "jacob",
    "james", "jasmine", "jayden", "john", "joseph", "josh", "joshua", "julia", "justin",
    "kaitlyn", "kate", "katie", "kayla", "kevin", "lauren", "leah", "liam", "lily", "logan",
    "lucas", "luke", "madison", "mason", "matt", "matthew", "mia", "michael", "natalie",
    "nathan", "nicholas", "noah", "olivia", "owen", "rachel", "ryan", "sam", "samantha",
    "sarah", "sophia", "sophie", "thomas", "tyler", "victoria", "will", "william", "zoe",
}


def find_friend_name_hints(friends: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints = []
    for friend in friends:
        display_name = (friend.get("friend_display_name") or "").strip()
        username = (friend.get("friend_username") or "").strip()
        normalized = display_name.lower()
        if not display_name or display_name == username:
            continue
        if normalized in COMMON_FIRST_NAMES:
            hints.append(
                {
                    "friend_user_id": friend.get("friend_user_id"),
                    "friend_username": username,
                    "friend_display_name": display_name,
                    "hint_type": "display_name_matches_common_first_name",
                    "source": "Roblox public friends displayName",
                }
            )
    return hints
