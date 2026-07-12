# Roblox OSINT /// Public Account Lookup

Plain Python command-line utility for legal and educational Roblox public account research.

The tool collects only public account data from official Roblox public API endpoints when available. Roblox Open Cloud API keys are loaded from `.env` and are sent only with the `x-api-key` header for endpoints that require them.

## Data collected

- username
- display name
- user ID
- profile URL
- avatar thumbnail
- avatar customization objects, body colors, scales, and avatar type when publicly available
- account anniversary/join date from Roblox's public profile creation timestamp
- public friend count
- public friend IDs when the friends list is visible
- public follower count
- public following count
- public groups and roles
- public badges
- public collectible inventory only when visible and officially accessible
- public Roblox games/experiences created by the user
- previous usernames when returned by Roblox's public username-history endpoint
- public BloxFlip/RBXFlip lookup results when those external public endpoints return data
- local SQLite lookup cache in `output/osint_cache.sqlite`
- account creation date when returned by Roblox

## Data not collected

This tool does not collect or attempt to infer target age, target birthday, private inventory data, hidden profile data, email addresses, passwords, CAPTCHA tokens, browser storage, deleted content, restricted data, or anything requiring bypasses, scraping protection evasion, exploitation, or impersonation. Account anniversary is calculated only from the public Roblox account creation timestamp. `.ROBLOSECURITY` can be read only from your local `cookies.txt` when you explicitly pass `--use-cookies`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Set `ROBLOX_OPEN_CLOUD_API_KEY` in `.env` only if you add an endpoint that requires a Roblox Open Cloud API key.

## Usage

Look up by username:

```bash
python main.py example_user
```

This opens a data menu:

```text
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                  ║
║   ██▀███   ▒█████    ▄▄▄▄    ██▓    ▒█████  ▒██   ██▒ ▒█████    ██████   ██ ███▄    █ ▄▄▄█████▓  ║
║  ▓██ ▒ ██▒▒██▒  ██▒ ▓█████▄ ▓██▒   ▒██▒  ██▒▒▒ █ █ ▒░▒██▒  ██▒▒██    ▒ ▒▓██ ██ ▀█   █ ▓  ██▒ ▓▒  ║
║  ▓██ ░▄█ ▒▒██░  ██▒ ▒██▒ ▄██▒██░   ▒██░  ██▒░░  █   ░▒██░  ██▒░ ▓██▄   ░▒██▓██  ▀█ ██▒▒ ▓██░ ▒░  ║
║  ▒██▀▀█▄  ▒██   ██░ ▒██░█▀  ▒██░   ▒██   ██░ ░ █ █ ▒ ▒██   ██░  ▒   ██▒ ░██▓██▒  ▐▌██▒░ ▓██▓ ░   ║
║  ░██▓ ▒██▒░ ████▓▒░▒░▓█  ▀█▓░██████░ ████▓▒░▒██▒ ▒██▒░ ████▓▒░▒██████▒▒ ░██▒██░   ▓██░  ▒██▒ ░   ║
║  ░ ▒▓ ░▒▓░░ ▒░▒░▒░ ░░▒▓███▀▒░ ▒░▓  ░ ▒░▒░▒░ ▒▒ ░ ░▓ ░░ ▒░▒░▒░ ▒ ▒▓▒ ▒ ░ ░▓ ░ ▒░   ▒ ▒   ▒ ░░     ║
║    ░▒ ░ ▒░  ░ ▒ ▒░ ░▒░▒   ░ ░ ░ ▒    ░ ▒ ▒░ ░░   ░▒ ░  ░ ▒ ▒░ ░ ░▒  ░    ▒ ░ ░░   ░ ▒░    ░      ║
║     ░   ░ ░ ░ ░ ▒    ░    ░   ░ ░  ░ ░ ░ ▒   ░    ░  ░ ░ ░ ▒  ░  ░  ░    ▒    ░   ░ ░   ░ ░      ║
║     ░         ░ ░  ░ ░          ░      ░ ░   ░    ░      ░ ░        ░    ░          ░            ║
║                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
+ Target ---------------------------------------------------+
| example_user                                             |
+----------------------------------------------------------+
+ Data Numbers -------------------------------------------+
| Data                                                     |
| ├── [1] Profile, counts, avatar, and account anniversary |
| ├── [2] Groups                                           |
| ├── [3] Badges from inventory page [may require          |
| │   --use-cookies]                                       |
| ├── [4] Collectible inventory [may require --use-cookies]|
| ├── [5] Friends and friend name finder                   |
| ├── [6] Public Roblox games/experiences created by user  |
| ├── [7] Previous usernames                               |
| ├── [8] Authenticated account age bracket + birthdate    |
| │   [cookie owner only]                                  |
| └── [9] Gambling information (BloxFlip/RBXFlip public    |
|     lookup)                                              |
|                                                          |
| Selection                                                |
| ├── [all] Everything                                     |
| └── examples: 1, 9, 5,9                                  |
+----------------------------------------------------------+
+ Navigation ---------------------------------------------+
| Commands                                                 |
| ├── max-pages                                            |
| │   └── Limit paginated sections, such as badges and     |
| │       inventory, to 2 pages.                           |
| ├── skip-inventory                                       |
| │   └── Skip the collectible inventory lookup.           |
| └── help                                                 |
|     └── Show full help and examples.                     |
+----------------------------------------------------------+
```

At the menu prompt, enter any data number directly. For example, `1` collects profile only, `2` collects groups only, `9` collects gambling information only, and `5,9` collects friends plus gambling information. You can also paste a full command such as `python main.py example_user --data 9`.

Show app help:

```bash
python main.py help
```

You can also run `python main.py` and type `help` at the prompt.
Running `python main.py` without arguments prints common commands first.

Look up by user ID:

```bash
python main.py 123456
```

Limit paginated reads:

```bash
python main.py example_user --max-pages 2
```

This limits paginated sections, such as badges and inventory, to 2 pages.

Skip public collectible inventory lookup:

```bash
python main.py example_user --skip-inventory
```

This skips the collectible inventory lookup.

Use local cookies for authenticated Roblox avatar/outfit endpoints:

```bash
python main.py example_user --use-cookies
```

This reads `.ROBLOSECURITY` from `cookies.txt`. The file is ignored by `.gitignore`; keep it private and use it only for accounts you are authorized to access.

Collect only specific data by number:

```text
python main.py example_user --data 9

[1] = profile, counts, and avatar
[2] = groups
[3] = badges from the inventory page; may require --use-cookies
[4] = collectible inventory; may require --use-cookies
[5] = friends and friend name finder
[6] = public Roblox games/experiences created by user
[7] = previous usernames
[8] = authenticated account age bracket + birthdate, only when target matches cookie owner
[9] = gambling information from public BloxFlip/RBXFlip lookup endpoints
all = everything
```

The `python main.py help` command shows the interactive data options:

```text
Data scraping numbers:
  [1] Profile, counts, avatar, and account anniversary
  [2] Groups
  [3] Badges from inventory page [may require --use-cookies]
  [4] Collectible inventory [may require --use-cookies]
  [5] Friends and friend name finder
  [6] Public Roblox games/experiences created by user
  [7] Previous usernames
  [8] Authenticated account age bracket + birthdate [cookie owner only]
  [9] Gambling information (BloxFlip/RBXFlip public lookup)
  [all] Everything

Examples: enter 1 for profile only, 9 for gambling only, or 5,9 for both.
```

Examples:

```bash
python main.py example_user --data 1
python main.py example_user --data 9
python main.py example_user --data 5,9
python main.py example_user --data 2,5
python main.py 123456 --data friends
```

## Example terminal output

```text
Roblox Public Account Lookup
Target: example_user
User ID: 123456
Status: Fetching public profile...
Status: Fetching public avatar customization...
Status: Fetching public group total...
Status: Fetching public badges...
Status: Fetching public collectible inventory if visible...
Saved JSON: output\example_user_2026-06-17.json
Saved CSV: output\example_user_2026-06-17.csv
```

## Example JSON format

```json
{
  "scan": {
    "target": "example_user",
    "resolved_user_id": 123456,
    "resolved_username": "example_user",
    "profile_summary": {
      "profile": 1,
      "avatar_image": 1,
      "avatar_objects": 2,
      "groups": 3,
      "group_records_included": 0,
      "badges": 0,
      "inventory": 0,
      "friends": 1
    },
    "total_records": 8,
    "timestamp_utc": "2026-06-17T15:00:00+00:00",
    "source": "Roblox public APIs and public Open Cloud-compatible access when required"
  },
  "profile": {
    "user_id": 123456,
    "username": "example_user",
    "display_name": "Example",
    "description": "Public profile text",
    "created": "2016-01-01T00:00:00.000Z",
    "account_anniversary": {
      "join_date": "2016-01-01",
      "join_date_utc": "2016-01-01T00:00:00+00:00",
      "anniversary_month": 1,
      "anniversary_day": 1,
      "anniversary_label": "Jan 1, 2016",
      "is_anniversary_today": false,
      "source": "Roblox public profile created timestamp"
    },
    "is_banned": false,
    "profile_url": "https://www.roblox.com/users/123456/profile",
    "avatar_thumbnail": "https://tr.rbxcdn.com/example.png",
    "avatar_customization": {
      "visible": true,
      "reason": null,
      "avatar_details_error": null,
      "avatar_type": "R15",
      "object_names": ["Example Hat"],
      "outfit_object_names": ["Example Hat"],
      "body_colors": {},
      "scales": {},
      "assets": [
        {
          "asset_id": 111,
          "name": "Example Hat",
          "asset_type_id": 8,
          "asset_type": "Hat",
          "current_version_id": 222
        }
      ]
    },
    "friend_count": 12,
    "follower_count": 34,
    "following_count": 56
  },
  "groups": [],
  "badges": {
    "visible": false,
    "reason": "Roblox denied the inventory badges endpoint. Try --use-cookies with a valid logged-in Roblox cookie.",
    "items": []
  },
  "inventory": {
    "visible": false,
    "reason": "Public collectible inventory is unavailable or hidden.",
    "items": []
  },
  "friends": {
    "visible": true,
    "reason": null,
    "items": [
      {
        "friend_user_id": 234567,
        "friend_username": "friend_user",
        "friend_display_name": "Friend",
        "is_banned": false,
        "profile_url": "https://www.roblox.com/users/234567/profile"
      }
    ]
  }
}
```

## Output files

Results are written to:

- `output/<username>_<date>.json`
- `output/<username>_<date>.csv`

Request logs are written to:

- `logs/roblox_lookup_<timestamp>.log`

## API behavior

The shared request helper:

- uses timeouts
- retries temporary failures
- handles HTTP 429 rate limits with `Retry-After` when present
- follows cursor pagination
- logs request method, URL, status code, elapsed time, and parameters
- prints clear terminal errors for failed lookups

Roblox Open Cloud documentation:

- https://create.roblox.com/docs/en-us/cloud
- https://create.roblox.com/docs/en-us/cloud/auth/api-keys

This tool collects and analyzes publicly available information and does not bypass Roblox security or access private data. I am not responsible for any misuse, abuse, or consequences resulting from the use of this tool. 
