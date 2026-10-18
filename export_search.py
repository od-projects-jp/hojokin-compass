
"""Hojokin Compass: SQLiteから検索用の軽量JSONを生成する。"""
import json
import sqlite3
import datetime as dt
from pathlib import Path

DB = "hojokin.sqlite"
OUTPUT = Path("public/data/subsidies.json")


def parse_json(value):
    try:
        return json.loads(value) if value else {}
    except (ValueError, TypeError):
        return {}


def first_value(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def export():
    if not Path(DB).exists():
        raise FileNotFoundError(f"Database not found: {DB}")

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    subsidies = conn.execute(
        "SELECT id, title, area, max_amount, agency, raw_json "
        "FROM subsidies ORDER BY title"
    ).fetchall()

    rounds = conn.execute(
        "SELECT subsidy_id, id, start_at, end_at, area "
        "FROM rounds"
    ).fetchall()

    by_subsidy = {}
    for row in rounds:
        by_subsidy.setdefault(row["subsidy_id"], []).append({
            "id": row["id"],
            "start_at": row["start_at"],
            "end_at": row["end_at"],
            "area": row["area"],
        })

    records = []
    for row in subsidies:
        raw = parse_json(row["raw_json"])
        record = {
            "id": row["id"],
            "title": first_value(row["title"], raw.get("title")),
            "area": first_value(row["area"], raw.get("target_area_search")),
            "max_amount": row["max_amount"],
            "agency": first_value(row["agency"], raw.get("institution_name")),
            "purpose": raw.get("use_purpose"),
            "industry": raw.get("target_industry"),
            "subsidy_rate": raw.get("subsidy_rate"),
            "rounds": by_subsidy.get(row["id"], []),
            "source": "Jグランツ",
        }
        records.append(record)

    output = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total": len(records),
        "subsidies": records,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    conn.close()
    print(f"Exported {len(records)} subsidies to {OUTPUT}")
    print(f"File size: {OUTPUT.stat().st_size:,} bytes")


if __name__ == "__main__":
    export()
