import json
import sqlite3
from pathlib import Path
from typing import Any


def store_lookup_result(db_path: Path, result: dict[str, Any]) -> dict[str, Any]:
    db_path.parent.mkdir(exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS lookups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp_utc TEXT NOT NULL,
                target TEXT NOT NULL,
                resolved_user_id INTEGER,
                resolved_username TEXT,
                result_json TEXT NOT NULL
            )
            """
        )
        cursor = connection.execute(
            """
            INSERT INTO lookups (
                timestamp_utc,
                target,
                resolved_user_id,
                resolved_username,
                result_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                result["scan"]["timestamp_utc"],
                result["scan"]["target"],
                result["scan"].get("resolved_user_id"),
                result["scan"].get("resolved_username"),
                json.dumps(result, ensure_ascii=False),
            ),
        )
        connection.commit()
        return {
            "enabled": True,
            "db_path": str(db_path),
            "lookup_id": cursor.lastrowid,
        }
