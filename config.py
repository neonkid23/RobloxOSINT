import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"
CACHE_DB_PATH = OUTPUT_DIR / "osint_cache.sqlite"
DEFAULT_COOKIES_FILE = BASE_DIR / "cookies.txt"

load_dotenv(BASE_DIR / ".env")

ROBLOX_OPEN_CLOUD_API_KEY = os.getenv("ROBLOX_OPEN_CLOUD_API_KEY", "").strip()

DEFAULT_TIMEOUT_SECONDS = int(os.getenv("ROBLOX_TIMEOUT_SECONDS", "20"))
DEFAULT_RETRIES = int(os.getenv("ROBLOX_RETRIES", "3"))
DEFAULT_RETRY_DELAY_SECONDS = float(os.getenv("ROBLOX_RETRY_DELAY_SECONDS", "1.5"))
DEFAULT_PAGE_LIMIT = int(os.getenv("ROBLOX_PAGE_LIMIT", "100"))
