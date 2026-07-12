import argparse
import csv
import json
import logging
import os
import shutil
import shlex
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from api.account import get_authenticated_account_info
from api.avatar import get_avatar_customization
from api.badges import get_public_badges
from api.cache import store_lookup_result
from api.client import RobloxApiError
from api.cookies import load_roblox_cookie_header
from api.friend_names import find_friend_name_hints
from api.friends import get_public_friends
from api.gambling import get_public_gambling_info
from api.games import get_public_user_games
from api.groups import get_public_groups
from api.inventory import get_public_collectibles
from api.thumbnails import get_avatar_thumbnail
from api.users import get_public_counts, get_public_profile, resolve_user_id
from api.usernames import get_previous_usernames
from config import CACHE_DB_PATH, DEFAULT_COOKIES_FILE, LOG_DIR, OUTPUT_DIR


DATA_OPTIONS = {
    "1": "profile",
    "2": "groups",
    "3": "badges",
    "4": "inventory",
    "5": "friends",
    "6": "public_games",
    "7": "previous_usernames",
    "8": "authenticated_account",
    "9": "gambling",
}
DATA_LABELS = {
    "profile": "Profile, counts, avatar, and account anniversary",
    "groups": "Groups",
    "badges": "Badges from inventory page",
    "inventory": "Collectible inventory",
    "friends": "Friends and friend name finder",
    "public_games": "Public Roblox games/experiences created by user",
    "previous_usernames": "Previous usernames",
    "authenticated_account": "Authenticated account age bracket + birthdate",
    "gambling": "Gambling information (BloxFlip/RBXFlip public lookup)",
}
DATA_NOTES = {
    "badges": "may require --use-cookies",
    "inventory": "may require --use-cookies",
    "authenticated_account": "cookie owner only",
}
DATA_ALIASES = {name: name for name in DATA_OPTIONS.values()} | {"all": "all"}
DATA_ALIAS_REDIRECTS = {
    "games": "public_games",
    "public-games": "public_games",
    "game-played": "public_games",
    "friends-name-finder": "friends",
    "friend-names": "friends",
    "previous": "previous_usernames",
    "previous-usernames": "previous_usernames",
}
DATA_ALIASES.update(
    {
        "personal": "authenticated_account",
        "personal-info": "authenticated_account",
        "age": "authenticated_account",
        "birthday": "authenticated_account",
        "authenticated-account": "authenticated_account",
        "bloxflip": "gambling",
        "rbxflip": "gambling",
    }
)

MIN_UI_WIDTH = 48
MAX_UI_WIDTH = 92
ANSI_RED = "\033[31m"
ANSI_RESET = "\033[0m"
TITLE_ART = [
    "ROBLOXOSINT",
]
TITLE_ART_WIDE = [
    " ██▀███   ▒█████    ▄▄▄▄    ██▓    ▒█████  ▒██   ██▒ ▒█████    ██████   ██ ███▄    █ ▄▄▄█████▓",
    "▓██ ▒ ██▒▒██▒  ██▒ ▓█████▄ ▓██▒   ▒██▒  ██▒▒▒ █ █ ▒░▒██▒  ██▒▒██    ▒ ▒▓██ ██ ▀█   █ ▓  ██▒ ▓▒",
    "▓██ ░▄█ ▒▒██░  ██▒ ▒██▒ ▄██▒██░   ▒██░  ██▒░░  █   ░▒██░  ██▒░ ▓██▄   ░▒██▓██  ▀█ ██▒▒ ▓██░ ▒░",
    "▒██▀▀█▄  ▒██   ██░ ▒██░█▀  ▒██░   ▒██   ██░ ░ █ █ ▒ ▒██   ██░  ▒   ██▒ ░██▓██▒  ▐▌██▒░ ▓██▓ ░ ",
    "░██▓ ▒██▒░ ████▓▒░▒░▓█  ▀█▓░██████░ ████▓▒░▒██▒ ▒██▒░ ████▓▒░▒██████▒▒ ░██▒██░   ▓██░  ▒██▒ ░ ",
    "░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░░▒▓███▀▒░ ▒░▓  ░ ▒░▒░▒░ ▒▒ ░ ░▓ ░░ ▒░▒░▒░ ▒ ▒▓▒ ▒ ░ ░▓ ░ ▒░   ▒ ▒   ▒ ░░   ",
    "  ░▒ ░ ▒░  ░ ▒ ▒░ ░▒░▒   ░ ░ ░ ▒    ░ ▒ ▒░ ░░   ░▒ ░  ░ ▒ ▒░ ░ ░▒  ░    ▒ ░ ░░   ░ ▒░    ░    ",
    "   ░   ░ ░ ░ ░ ▒    ░    ░   ░ ░  ░ ░ ░ ▒   ░    ░  ░ ░ ░ ▒  ░  ░  ░    ▒    ░   ░ ░   ░ ░    ",
    "   ░         ░ ░  ░ ░          ░      ░ ░   ░    ░      ░ ░        ░    ░          ░          ",
]


def terminal_ui_width() -> int:
    width = shutil.get_terminal_size((80, 20)).columns
    return max(MIN_UI_WIDTH, min(MAX_UI_WIDTH, width))


def terminal_title_width(title_lines: list[str]) -> int:
    width = shutil.get_terminal_size((80, 20)).columns
    art_width = max(len(line) for line in title_lines) + 6
    return max(MIN_UI_WIDTH, width, art_width)


def print_panel(title: str, rows: list[str] | None = None) -> None:
    width = terminal_ui_width()
    content_width = width - 4
    title_text = f" {title} "
    rule_width = max(1, width - len(title_text) - 2)
    print("+" + title_text + "-" * rule_width + "+")
    for row in rows or []:
        if row == "":
            print("|" + " " * (width - 2) + "|")
            continue
        for wrapped in wrap_ui_row(row, content_width):
            print(f"| {wrapped.ljust(content_width)} |")
    print("+" + "-" * (width - 2) + "+")


def print_title_banner() -> None:
    width = terminal_title_width(TITLE_ART_WIDE)
    content_width = width - 2
    title_lines = TITLE_ART_WIDE if all(len(line) <= content_width for line in TITLE_ART_WIDE) else TITLE_ART
    print("╔" + "═" * content_width + "╗")
    print("║" + " " * content_width + "║")
    for line in title_lines:
        print_centered_box_line(colorize_red(line), visible_width=len(line), content_width=content_width)
    print("║" + " " * content_width + "║")
    print("╚" + "═" * content_width + "╝")


def print_centered_box_line(text: str, *, visible_width: int, content_width: int) -> None:
    left_padding = max(0, (content_width - visible_width) // 2)
    right_padding = max(0, content_width - visible_width - left_padding)
    print("║" + " " * left_padding + text + " " * right_padding + "║")


def colorize_red(text: str) -> str:
    if os.getenv("NO_COLOR"):
        return text
    return f"{ANSI_RED}{text}{ANSI_RESET}"


def wrap_ui_row(row: str, width: int) -> list[str]:
    if len(row) <= width:
        return [row]
    stripped = row.lstrip()
    indent = row[: len(row) - len(stripped)]
    continuation = tree_continuation_prefix(row, indent)
    wrapped = textwrap.wrap(
        stripped,
        width=max(16, width - len(indent)),
        break_long_words=False,
        break_on_hyphens=False,
    )
    if not wrapped:
        return [""]
    lines = [indent + wrapped[0]]
    follow_width = max(16, width - len(continuation))
    for part in wrapped[1:]:
        if len(part) <= follow_width:
            lines.append(continuation + part)
        else:
            lines.extend(continuation + chunk for chunk in textwrap.wrap(part, width=follow_width))
    return lines


def tree_continuation_prefix(row: str, fallback_indent: str) -> str:
    marker_index = max(row.find("├── "), row.find("└── "))
    if marker_index >= 0:
        branch = "│   " if "├── " in row else "    "
        return row[:marker_index] + branch
    return fallback_indent


def data_tree_rows() -> list[str]:
    rows = ["Data"]
    option_items = list(DATA_OPTIONS.items())
    for index, (number, data_name) in enumerate(option_items):
        connector = "└──" if index == len(option_items) - 1 else "├──"
        note = DATA_NOTES.get(data_name)
        label = DATA_LABELS[data_name]
        suffix = f" [{note}]" if note else ""
        rows.append(f"{connector} [{number}] {label}{suffix}")
    rows.extend(["", "Selection"])
    rows.append("├── [all] Everything")
    rows.append("└── examples: 1, 9, 5,9")
    return rows


def command_tree_rows() -> list[str]:
    return [
        "Commands",
        "├── max-pages",
        "│   └── Limit paginated sections, such as badges and inventory, to 2 pages.",
        "├── skip-inventory",
        "│   └── Skip the collectible inventory lookup.",
        "└── help",
        "    └── Show full help and examples.",
    ]


def configure_output_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def clear_terminal() -> None:
    """Start each interactive section at the top of the terminal window."""
    if sys.stdout.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def main() -> int:
    configure_output_encoding()
    clear_terminal()
    print_title_banner()
    args = parse_args()
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)

    scan_started = datetime.now(timezone.utc)
    timestamp = scan_started.strftime("%Y-%m-%dT%H-%M-%SZ")
    setup_logging(LOG_DIR / f"roblox_lookup_{timestamp}.log")

    print_panel("Target", [args.target])

    try:
        args.data = normalize_data_selection(args.data or "all")
        selected_data = parse_data_selection(args.data)
        validate_target(args.target)
        cookie_header = load_cookie_header_if_enabled(args)
        validate_cookie_requirements(selected_data, cookie_header)
        print_selected_data_summary(args.data, selected_data)
        user_id = resolve_user_id(args.target)
        print(f"User ID: {user_id}")

        print("Status: Fetching public profile...")
        profile = get_public_profile(user_id)
        profile["account_anniversary"] = build_account_anniversary(profile.get("created"), scan_started)
        counts = {}
        thumbnail = fetch_optional_avatar_thumbnail(user_id)
        print("Status: Fetching public avatar customization...")
        avatar_customization = fetch_optional_avatar_customization(user_id, cookie_header=cookie_header)
        if "profile" in selected_data:
            counts = fetch_optional_counts(user_id)

        print("Status: Fetching public group total...")
        all_groups = fetch_optional_groups(user_id)
        groups = []
        if "groups" in selected_data:
            groups = all_groups

        badges = {"visible": False, "reason": "Not selected.", "items": []}
        if "badges" in selected_data:
            print("Status: Fetching public badges...")
            badges = fetch_optional_badges(user_id, max_pages=args.max_pages, cookie_header=cookie_header)

        friends = {"visible": False, "reason": "Not selected.", "items": []}
        if "friends" in selected_data:
            print("Status: Fetching public friends...")
            friends = fetch_optional_friends(user_id)
        friend_name_hints = {
            "visible": friends.get("visible", False),
            "reason": friends.get("reason"),
            "items": find_friend_name_hints(friends.get("items", [])) if friends.get("items") else [],
        }

        inventory = {"visible": False, "reason": "Not selected.", "items": []}
        if "inventory" in selected_data and args.skip_inventory:
            inventory = {"visible": False, "reason": "Skipped by command-line option.", "items": []}
        elif "inventory" in selected_data:
            print("Status: Fetching public collectible inventory if visible...")
            inventory = get_public_collectibles(user_id, max_pages=args.max_pages)

        public_games = {"visible": False, "reason": "Not selected.", "items": []}
        if "public_games" in selected_data:
            print("Status: Fetching public games/experiences created by user...")
            public_games = fetch_optional_public_games(user_id, max_pages=args.max_pages)

        previous_usernames = {"visible": False, "reason": "Not selected.", "items": []}
        if "previous_usernames" in selected_data:
            print("Status: Fetching previous usernames...")
            previous_usernames = fetch_optional_previous_usernames(user_id, max_pages=args.max_pages)

        authenticated_account = {"visible": False, "reason": "Not selected.", "data": None}
        if "authenticated_account" in selected_data:
            print("Status: Fetching authenticated account age/birthdate if target matches cookie user...")
            authenticated_account = fetch_optional_authenticated_account(user_id, cookie_header)

        gambling = {"visible": False, "reason": "Not selected.", "items": []}
        if "gambling" in selected_data:
            print("Status: Fetching public BloxFlip/RBXFlip gambling information...")
            gambling = fetch_optional_gambling(user_id)

        result = build_result(
            args.target,
            selected_data,
            scan_started,
            profile,
            counts,
            thumbnail,
            avatar_customization,
            groups,
            len(all_groups),
            badges,
            inventory,
            friends,
            friend_name_hints,
            public_games,
            previous_usernames,
            authenticated_account,
            gambling,
        )
        basename = safe_filename(profile.get("username") or str(user_id), scan_started)
        json_path = OUTPUT_DIR / f"{basename}.json"
        csv_path = OUTPUT_DIR / f"{basename}.csv"

        result["scan"]["cache"] = store_lookup_result(CACHE_DB_PATH, result)
        write_json(json_path, result)
        write_csv(csv_path, result)

        print(f"Saved JSON: {json_path}")
        print(f"Saved CSV: {csv_path}")
        return 0
    except RobloxApiError as exc:
        logging.error("Lookup failed: %s", exc)
        print(f"Error: {exc}")
        return 1


def parse_args() -> argparse.Namespace:
    parser = build_parser()
    args = parser.parse_args()
    if args.target and args.target.lower() == "help":
        print_app_help()
        raise SystemExit(0)
    if not args.target:
        if not sys.stdin.isatty():
            parser.error("target is required when running non-interactively")
        print_command_overview()
        while True:
            target_input = input("Roblox username or numeric user ID (or help): ").strip()
            if target_input.lower() == "help":
                print_app_help()
                continue
            pasted_args = parse_pasted_main_command(parser, target_input)
            if pasted_args:
                args = pasted_args
                if args.target and args.target.lower() == "help":
                    print_app_help()
                    continue
                if args.target:
                    if args.data is None and args.max_pages is None and not args.skip_inventory:
                        apply_target_action_menu(args)
                    return args
                print("Target cannot be empty. Type help for examples.")
                continue
            args.target = target_input
            if args.target:
                apply_target_action_menu(args)
                return args
            print("Target cannot be empty. Type help for examples.")
    elif args.data is None and args.max_pages is None and not args.skip_inventory and sys.stdin.isatty():
        apply_target_action_menu(args)
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect public Roblox account information through official public endpoints.",
    )
    parser.add_argument("target", nargs="?", help="Roblox username or numeric user ID")
    parser.add_argument("--max-pages", type=int, default=None, help="Maximum pages to read for paginated endpoints")
    parser.add_argument(
        "--data",
        default=None,
        help="Data to collect: 1=profile, 2=groups, 3=badges from inventory page, 4=inventory, 5=friends and friend name finder, 6=public games, 7=previous usernames, 8=authenticated account self info, 9=BloxFlip/RBXFlip, all=everything.",
    )
    parser.add_argument("--skip-inventory", action="store_true", help="Skip public collectible inventory lookup")
    parser.add_argument(
        "--use-cookies",
        action="store_true",
        help="Read cookies.txt and use its .ROBLOSECURITY cookie for endpoints that require your authenticated Roblox session",
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        default=DEFAULT_COOKIES_FILE,
        help=f"Path to cookies.txt when --use-cookies is enabled. Default: {DEFAULT_COOKIES_FILE}",
    )
    return parser


def parse_pasted_main_command(parser: argparse.ArgumentParser, command_text: str) -> argparse.Namespace | None:
    try:
        parts = shlex.split(command_text)
    except ValueError:
        parts = command_text.split()

    if len(parts) >= 2 and is_python_command(parts[0]) and Path(parts[1]).name.lower() == "main.py":
        return parser.parse_args(parts[2:])
    if parts and Path(parts[0]).name.lower() == "main.py":
        return parser.parse_args(parts[1:])
    return None


def is_python_command(command: str) -> bool:
    command_name = Path(command).name.lower()
    return command_name in {"python", "python.exe", "py", "py.exe"}


def validate_target(target: str) -> None:
    lowered = target.lower().strip()
    if not lowered:
        raise RobloxApiError("Target cannot be empty. Use: python main.py <username-or-user-id>")
    if lowered in {"python", "py", "main.py", "all", "help"} or " main.py " in f" {lowered} ":
        raise RobloxApiError(
            "That looks like a command or menu input, not a Roblox username. "
            "Use: python main.py <username-or-user-id> --data 1,5"
        )
    if any(char.isspace() for char in target):
        raise RobloxApiError(
            "Roblox usernames and numeric IDs cannot contain spaces. "
            "If you pasted a command, run it at the terminal prompt or paste the full command when asked."
        )


def apply_target_action_menu(args: argparse.Namespace) -> None:
    print_target_action_menu(args.target)
    while True:
        choice = input("Data numbers to collect [all], command, or help: ").strip() or "all"
        pasted_args = parse_pasted_main_command(build_parser(), choice)
        if pasted_args and pasted_args.target:
            args.target = pasted_args.target
            args.max_pages = pasted_args.max_pages
            args.data = pasted_args.data
            args.skip_inventory = pasted_args.skip_inventory
            args.use_cookies = pasted_args.use_cookies
            args.cookies_file = pasted_args.cookies_file
            if args.data is None and args.max_pages is None and not args.skip_inventory:
                apply_target_action_menu(args)
            return
        if choice.lower() == "help":
            print_app_help()
            print_target_action_menu(args.target)
            continue
        if choice.lower() in {"max-pages", "max-pages 2", "--max-pages 2"}:
            args.max_pages = 2
            args.data = "all"
            return
        if choice.lower() in {"skip-inventory", "--skip-inventory", "skip"}:
            args.skip_inventory = True
            args.data = "all"
            return
        selection = normalize_data_selection(choice)
        try:
            parse_data_selection(selection)
        except RobloxApiError as exc:
            print(f"{exc}")
            print("Enter data numbers like 1, 9, 5,9, or all. You can also paste a full command.")
            continue
        args.data = selection
        if ask_yes_no("Use cookies.txt for authenticated avatar/outfit endpoints? [y/N]: "):
            args.use_cookies = True
        return


def prompt_for_data_selection(show_menu: bool = True) -> str:
    if show_menu:
        print_data_selection_menu()
    while True:
        selection = input("Data numbers to collect [all]: ").strip() or "all"
        selection = normalize_data_selection(selection)
        try:
            parse_data_selection(selection)
        except RobloxApiError as exc:
            print(f"{exc}")
            print("Use subnumbers like 1.1,1.5, regular numbers like 1,5, or type all.")
            continue
        return selection


def ask_yes_no(prompt: str) -> bool:
    return (input(prompt).strip().lower() in {"y", "yes"})


def validate_cookie_requirements(selected_data: set[str], cookie_header: str | None) -> None:
    if "authenticated_account" in selected_data and not cookie_header:
        raise RobloxApiError("Selection [8] requires cookies. Add --use-cookies to your command.")
    if "inventory" in selected_data and not cookie_header:
        print("Note: Selection [4] collectible inventory may be hidden unless you use --use-cookies.")


def print_selected_data_summary(selection: str, selected_data: set[str]) -> None:
    rows = [f"Selection: {selection}", "Selected data"]
    ordered_data = ordered_selected_data(selected_data)
    for index, data_name in enumerate(ordered_data):
        connector = "└──" if index == len(ordered_data) - 1 else "├──"
        rows.append(f"{connector} {DATA_LABELS.get(data_name, data_name)}")
    print_panel("Run Summary", rows)
    if len(selected_data) > 1:
        print("Note: comma-separated numbers collect each listed item. Use a single number to collect only that item.")
    if selected_data == {"gambling"}:
        print("Note: A basic Roblox profile is still fetched first to resolve the username/user ID.")


def ordered_selected_data(selected_data: set[str]) -> list[str]:
    ordered = []
    seen = set()
    for data_name in DATA_OPTIONS.values():
        if data_name in selected_data and data_name not in seen:
            ordered.append(data_name)
            seen.add(data_name)
    return ordered


def print_target_action_menu(target: str) -> None:
    clear_terminal()
    print_panel("ROBLOXOSINT", ["Section: Data Selection"])
    print_panel("Target", [target])
    print_data_menu()
    print_panel("Navigation", ["Enter a data number, all, help, max-pages, or skip-inventory."])
    print()


def print_command_overview() -> None:
    print_panel(
        "Start",
        [
            "Enter a Roblox username or numeric user ID below.",
            "The data selection menu opens on the next screen.",
            "Type help to open the full command guide.",
        ],
    )
    print()


def print_data_command() -> None:
    print_profile_data_option()


def print_profile_data_option() -> None:
    print_data_menu(include_title=False)
    print_panel(
        "Examples",
        [
            "├── 1 = profile only",
            "├── 9 = gambling only",
            "├── 5,9 = friends plus gambling",
            "├── python main.py <username-or-user-id> --data 9",
            "└── add --use-cookies to use local cookies.txt for authenticated avatar/outfit endpoints",
        ],
    )


def print_data_selection_menu() -> None:
    print()
    print_panel(
        "Data Menu",
        [
            "Enter one number for one data type, or comma-separated numbers for multiple data types.",
            "Examples: 1 = profile only, 9 = gambling only, 1,9 = profile and gambling.",
        ],
    )
    print_data_menu(prefix="  ")


def print_app_help() -> None:
    clear_terminal()
    print_panel("ROBLOXOSINT", ["Section: Help"])
    print_panel(
        "Help",
        [
            "Usage",
            "├── python main.py <username-or-user-id>",
            "│   └── Open the interactive data menu.",
            "└── python main.py help",
            "    └── Show this screen.",
        ],
    )
    print_profile_data_option()
    print_panel("Navigation", command_tree_rows())
    print_panel(
        "Commands",
        [
            "├── python main.py Builderman",
            "├── python main.py 156",
            "├── python main.py Builderman --data 1",
            "├── python main.py Builderman --data 5,9",
            "└── python main.py Builderman --data 9",
        ],
    )


def print_data_menu(prefix: str = "", include_title: bool = True) -> None:
    rows = data_tree_rows()
    if not include_title:
        rows = rows[1:]
    if prefix:
        rows = [f"{prefix}{row}" if row else row for row in rows]
    print_panel("Data Numbers", rows)


def parse_data_selection(selection: str | None) -> set[str]:
    if not selection:
        return set(DATA_OPTIONS.values())

    selected: set[str] = set()
    for raw_item in selection.split(","):
        item = raw_item.strip().lower()
        if not item:
            continue
        if item == "all":
            return set(DATA_OPTIONS.values())
        if item in DATA_OPTIONS:
            selected.add(DATA_OPTIONS[item])
            continue
        if item in DATA_ALIASES and item != "all":
            selected.add(DATA_ALIASES[item])
            continue
        if item in DATA_ALIAS_REDIRECTS:
            alias_value = DATA_ALIAS_REDIRECTS[item]
            if alias_value in DATA_ALIASES:
                selected.add(alias_value)
                continue
            raise RobloxApiError(alias_value)
        valid = ", ".join([f"{number}={name}" for number, name in DATA_OPTIONS.items()] + ["all"])
        raise RobloxApiError(f"Unknown data selection '{raw_item}'. Use: {valid}")

    if not selected:
        raise RobloxApiError("No data selections were provided.")
    return selected


def normalize_data_selection(selection: str) -> str:
    normalized = []
    for raw_item in selection.split(","):
        item = raw_item.strip().lower()
        if item.startswith("1.") and item[2:] in DATA_OPTIONS:
            item = item[2:]
        normalized.append(item)
    return ",".join(normalized)


def fetch_optional_badges(
    user_id: int,
    max_pages: int | None = None,
    cookie_header: str | None = None,
) -> dict[str, Any]:
    try:
        return {
            "visible": True,
            "reason": None,
            "items": get_public_badges(user_id, max_pages=max_pages, cookie_header=cookie_header),
        }
    except RobloxApiError as exc:
        logging.info("Public badges unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Roblox denied the inventory badges endpoint; continuing.")
        return {
            "visible": False,
            "reason": f"Roblox denied the inventory badges endpoint. Try --use-cookies with a valid logged-in Roblox cookie. Details: {exc}",
            "items": [],
        }


def fetch_optional_friends(user_id: int) -> dict[str, Any]:
    try:
        return {
            "visible": True,
            "reason": None,
            "items": get_public_friends(user_id),
        }
    except RobloxApiError as exc:
        logging.info("Public friends unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public friends are unavailable for this account; continuing.")
        return {
            "visible": False,
            "reason": "Public friends are unavailable or hidden.",
            "items": [],
        }


def fetch_optional_avatar_thumbnail(user_id: int) -> str | None:
    try:
        return get_avatar_thumbnail(user_id)
    except RobloxApiError as exc:
        logging.info("Public avatar thumbnail unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public avatar thumbnail is unavailable for this account; continuing.")
        return None


def load_cookie_header_if_enabled(args: argparse.Namespace) -> str | None:
    if not args.use_cookies:
        return None
    cookie_header = load_roblox_cookie_header(args.cookies_file)
    print(f"Status: Cookie mode enabled using {args.cookies_file}")
    return cookie_header


def fetch_optional_avatar_customization(user_id: int, cookie_header: str | None = None) -> dict[str, Any]:
    try:
        return get_avatar_customization(user_id, cookie_header=cookie_header)
    except RobloxApiError as exc:
        logging.info("Public avatar customization unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public avatar customization is unavailable for this account; continuing.")
        return {
            "visible": False,
            "reason": "Public avatar customization is unavailable.",
            "avatar_details_error": str(exc),
            "currently_wearing_error": None,
            "cookie_mode": bool(cookie_header),
            "avatar_type": None,
            "currently_wearing_asset_ids": [],
            "object_names": [],
            "outfit_object_names": [],
            "body_colors": {},
            "scales": {},
            "assets": [],
            "saved_outfits": {
                "visible": False,
                "reason": "Public avatar customization is unavailable.",
                "items": [],
            },
        }


def fetch_optional_counts(user_id: int) -> dict[str, Any]:
    try:
        return get_public_counts(user_id)
    except RobloxApiError as exc:
        logging.info("Public profile counts unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public profile counts are unavailable for this account; continuing.")
        return {
            "friend_count": None,
            "follower_count": None,
            "following_count": None,
        }


def fetch_optional_groups(user_id: int) -> list[dict[str, Any]]:
    try:
        return get_public_groups(user_id)
    except RobloxApiError as exc:
        logging.info("Public groups unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public groups are unavailable for this account; continuing.")
        return []


def fetch_optional_public_games(user_id: int, max_pages: int | None = None) -> dict[str, Any]:
    try:
        return {
            "visible": True,
            "reason": None,
            "items": get_public_user_games(user_id, max_pages=max_pages),
        }
    except RobloxApiError as exc:
        logging.info("Public games unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Public games/experiences are unavailable for this account; continuing.")
        return {
            "visible": False,
            "reason": f"Public games/experiences are unavailable: {exc}",
            "items": [],
        }


def fetch_optional_previous_usernames(user_id: int, max_pages: int | None = None) -> dict[str, Any]:
    try:
        return {
            "visible": True,
            "reason": None,
            "items": get_previous_usernames(user_id, max_pages=max_pages),
        }
    except RobloxApiError as exc:
        logging.info("Previous usernames unavailable for user_id=%s: %s", user_id, exc)
        print("Status: Previous usernames are unavailable for this account; continuing.")
        return {
            "visible": False,
            "reason": f"Previous usernames are unavailable: {exc}",
            "items": [],
        }


def fetch_optional_authenticated_account(user_id: int, cookie_header: str | None) -> dict[str, Any]:
    if not cookie_header:
        return {
            "visible": False,
            "reason": "Requires --use-cookies and a valid cookies.txt for the authenticated account.",
            "data": None,
        }

    try:
        account = get_authenticated_account_info(cookie_header)
    except RobloxApiError as exc:
        logging.info("Authenticated account info unavailable for target user_id=%s: %s", user_id, exc)
        return {
            "visible": False,
            "reason": f"Authenticated account info is unavailable: {exc}",
            "data": None,
        }

    if account.get("authenticated_user_id") != user_id:
        return {
            "visible": False,
            "reason": "Authenticated account age/birthdate belongs to the cookie owner only; target does not match cookie user.",
            "data": {
                "authenticated_user_id": account.get("authenticated_user_id"),
                "target_user_id": user_id,
            },
        }

    return {
        "visible": True,
        "reason": None,
        "data": account,
    }


def fetch_optional_gambling(user_id: int) -> dict[str, Any]:
    try:
        return {
            "visible": True,
            "reason": None,
            "items": get_public_gambling_info(user_id),
        }
    except RobloxApiError as exc:
        logging.info("Gambling info unavailable for user_id=%s: %s", user_id, exc)
        print("Status: BloxFlip/RBXFlip information is unavailable for this account; continuing.")
        return {
            "visible": False,
            "reason": f"BloxFlip/RBXFlip information is unavailable: {exc}",
            "items": [],
        }


def setup_logging(log_path: Path) -> None:
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)sZ %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def build_account_anniversary(created: str | None, scan_started: datetime) -> dict[str, Any]:
    if not created:
        return {
            "join_date": None,
            "anniversary_month": None,
            "anniversary_day": None,
            "is_anniversary_today": False,
            "reason": "Roblox did not return an account creation timestamp.",
        }

    normalized = created.replace("Z", "+00:00")
    try:
        created_at = datetime.fromisoformat(normalized)
    except ValueError:
        return {
            "join_date": None,
            "anniversary_month": None,
            "anniversary_day": None,
            "is_anniversary_today": False,
            "reason": f"Could not parse Roblox account creation timestamp: {created}",
        }

    created_at = created_at.astimezone(timezone.utc)
    today = scan_started.astimezone(timezone.utc)
    return {
        "join_date": created_at.date().isoformat(),
        "join_date_utc": created_at.isoformat(),
        "anniversary_month": created_at.month,
        "anniversary_day": created_at.day,
        "anniversary_label": created_at.strftime("%b %-d, %Y") if sys.platform != "win32" else created_at.strftime("%b %#d, %Y"),
        "is_anniversary_today": created_at.month == today.month and created_at.day == today.day,
        "source": "Roblox public profile created timestamp",
    }


def build_result(
    target: str,
    selected_data: set[str],
    scan_started: datetime,
    profile: dict[str, Any],
    counts: dict[str, Any],
    thumbnail: str | None,
    avatar_customization: dict[str, Any],
    groups: list[dict[str, Any]],
    group_total: int,
    badges: dict[str, Any],
    inventory: dict[str, Any],
    friends: dict[str, Any],
    friend_name_hints: dict[str, Any],
    public_games: dict[str, Any],
    previous_usernames: dict[str, Any],
    authenticated_account: dict[str, Any],
    gambling: dict[str, Any],
) -> dict[str, Any]:
    profile_summary = {
        "profile": 1,
        "avatar_image": 1 if thumbnail else 0,
        "avatar_objects": len(avatar_customization.get("assets", [])),
        "groups": group_total,
        "group_records_included": len(groups),
        "badges": len(badges.get("items", [])),
        "inventory": len(inventory.get("items", [])),
        "friends": len(friends.get("items", [])),
        "friend_name_hints": len(friend_name_hints.get("items", [])),
        "public_games": len(public_games.get("items", [])),
        "previous_usernames": len(previous_usernames.get("items", [])),
        "authenticated_account": 1 if authenticated_account.get("visible") else 0,
        "gambling": len(gambling.get("items", [])),
    }
    total_records = (
        profile_summary["profile"]
        + profile_summary["avatar_image"]
        + profile_summary["avatar_objects"]
        + profile_summary["groups"]
        + profile_summary["badges"]
        + profile_summary["inventory"]
        + profile_summary["friends"]
        + profile_summary["friend_name_hints"]
        + profile_summary["public_games"]
        + profile_summary["previous_usernames"]
        + profile_summary["authenticated_account"]
        + profile_summary["gambling"]
    )
    return {
        "scan": {
            "target": target,
            "resolved_user_id": profile.get("user_id"),
            "resolved_username": profile.get("username"),
            "profile_summary": profile_summary,
            "total_records": total_records,
            "timestamp_utc": scan_started.isoformat(),
            "source": "Roblox public APIs and public Open Cloud-compatible access when required",
        },
        "profile": {
            **profile,
            "avatar_thumbnail": thumbnail,
            "avatar_customization": avatar_customization,
            **counts,
        },
        "groups": groups,
        "badges": badges,
        "inventory": inventory,
        "friends": friends,
        "friend_name_hints": friend_name_hints,
        "public_games": public_games,
        "previous_usernames": previous_usernames,
        "authenticated_account": authenticated_account,
        "gambling": gambling,
        "unsupported": {
            "target_personal_information": "Age and birthdate are not public target profile data. Authenticated account age/birthdate is only returned when --use-cookies is enabled and the target matches the cookie owner.",
        },
    }


def write_json(path: Path, result: dict[str, Any]) -> None:
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, result: dict[str, Any]) -> None:
    profile = result["profile"]
    scan = result["scan"]
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=[
                "timestamp_utc",
                "target",
                "record_type",
                "user_id",
                "username",
                "display_name",
                "record_id",
                "name",
                "asset_type",
                "friend_user_id",
                "friend_username",
                "friend_display_name",
                "role_name",
                "url",
                "details_json",
            ],
        )
        writer.writeheader()
        if scan.get("profile_summary", {}).get("profile", 0):
            writer.writerow(
                {
                    "timestamp_utc": scan["timestamp_utc"],
                    "target": scan["target"],
                    "record_type": "profile",
                    "user_id": profile.get("user_id"),
                    "username": profile.get("username"),
                    "display_name": profile.get("display_name"),
                    "record_id": profile.get("user_id"),
                    "name": profile.get("username"),
                    "asset_type": "",
                    "friend_user_id": "",
                    "friend_username": "",
                    "friend_display_name": "",
                    "role_name": "",
                    "url": profile.get("profile_url"),
                    "details_json": json.dumps(profile, ensure_ascii=False),
                }
            )
        for asset in profile.get("avatar_customization", {}).get("assets", []):
            writer.writerow(
                csv_row(
                    scan,
                    profile,
                    "avatar_asset",
                    asset.get("asset_id"),
                    asset.get("name"),
                    "",
                    "",
                    asset,
                    asset_type=asset.get("asset_type"),
                )
            )
        for group in result["groups"]:
            writer.writerow(csv_row(scan, profile, "group", group.get("group_id"), group.get("name"), group.get("role_name"), "", group))
        for badge in result["badges"].get("items", []):
            writer.writerow(csv_row(scan, profile, "badge", badge.get("badge_id"), badge.get("name"), "", "", badge))
        for item in result["inventory"].get("items", []):
            writer.writerow(csv_row(scan, profile, "collectible", item.get("asset_id"), item.get("name"), "", "", item))
        for friend in result["friends"].get("items", []):
            writer.writerow(
                csv_row(
                    scan,
                    profile,
                    "friend",
                    friend.get("friend_user_id"),
                    friend.get("friend_username"),
                    "",
                    friend.get("profile_url") or "",
                    friend,
                    friend_user_id=friend.get("friend_user_id"),
                    friend_username=friend.get("friend_username"),
                    friend_display_name=friend.get("friend_display_name"),
                )
            )
        for hint in result["friend_name_hints"].get("items", []):
            writer.writerow(
                csv_row(
                    scan,
                    profile,
                    "friend_name_hint",
                    hint.get("friend_user_id"),
                    hint.get("friend_display_name"),
                    "",
                    "",
                    hint,
                    friend_user_id=hint.get("friend_user_id"),
                    friend_username=hint.get("friend_username"),
                    friend_display_name=hint.get("friend_display_name"),
                )
            )
        for game in result["public_games"].get("items", []):
            writer.writerow(csv_row(scan, profile, "public_game", game.get("game_id"), game.get("name"), "", game.get("url") or "", game))
        for username in result["previous_usernames"].get("items", []):
            writer.writerow(csv_row(scan, profile, "previous_username", username.get("previous_username"), username.get("previous_username"), "", "", username))
        if result["authenticated_account"].get("visible"):
            account = result["authenticated_account"].get("data") or {}
            writer.writerow(
                csv_row(
                    scan,
                    profile,
                    "authenticated_account",
                    account.get("authenticated_user_id"),
                    account.get("authenticated_username"),
                    "",
                    "",
                    account,
                )
            )
        for gambling_record in result["gambling"].get("items", []):
            writer.writerow(
                csv_row(
                    scan,
                    profile,
                    "gambling",
                    gambling_record.get("source"),
                    gambling_record.get("metric") or gambling_record.get("source"),
                    "",
                    "",
                    gambling_record,
                )
            )


def csv_row(
    scan: dict[str, Any],
    profile: dict[str, Any],
    record_type: str,
    record_id: Any,
    name: Any,
    role_name: Any,
    url: str,
    details: dict[str, Any],
    asset_type: Any = "",
    friend_user_id: Any = "",
    friend_username: Any = "",
    friend_display_name: Any = "",
) -> dict[str, Any]:
    return {
        "timestamp_utc": scan["timestamp_utc"],
        "target": scan["target"],
        "record_type": record_type,
        "user_id": profile.get("user_id"),
        "username": profile.get("username"),
        "display_name": profile.get("display_name"),
        "record_id": record_id,
        "name": name,
        "asset_type": asset_type,
        "friend_user_id": friend_user_id,
        "friend_username": friend_username,
        "friend_display_name": friend_display_name,
        "role_name": role_name,
        "url": url,
        "details_json": json.dumps(details, ensure_ascii=False),
    }


def safe_filename(username: str, scan_started: datetime) -> str:
    safe_name = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in username)
    return f"{safe_name}_{scan_started.strftime('%Y-%m-%d')}"


if __name__ == "__main__":
    raise SystemExit(main())
