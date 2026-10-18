"""Validate official application deadlines and report upcoming/expired dates.

This checks known fixed dates only; it never claims that a program is accepting applications.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path

VERIFIED_DIR = Path("public/data/individual_verified")
VERIFIED_ROOT = Path("public/data/individual_verified.json")
OUTPUT = Path("public/data/individual_deadlines.json")


def deadline_status(deadline, today):
    day = date.fromisoformat(deadline)
    remaining = (day - today).days
    if remaining < 0:
        return "期限経過", remaining
    if remaining <= 30:
        return "締切間近", remaining
    return "期限設定あり", remaining


def build_deadline_report(records, today):
    deadlines = []
    for item in records:
        deadline = item.get("application_deadline")
        if not deadline:
            continue
        state, days = deadline_status(deadline, today)
        deadlines.append({
            "title": item["title"],
            "area": item["area"],
            "application_deadline": deadline,
            "days_remaining": days,
            "status": state,
            "source": item["source"],
            "deadline_note": item.get("deadline_note", ""),
        })
    deadlines.sort(key=lambda x: (x["application_deadline"], x["area"], x["title"]))
    return {
        "as_of": today.isoformat(),
        "total_with_fixed_deadlines": len(deadlines),
        "upcoming_within_30_days": sum(x["status"] == "締切間近" for x in deadlines),
        "past_deadline": sum(x["status"] == "期限経過" for x in deadlines),
        "notice": "申請受付中であることは保証しません。受付状況・予算残額は公式サイトで確認してください。",
        "programs": deadlines,
    }


def main():
    from collect_individual import load_verified
    today = datetime.now(timezone.utc).date()
    report = build_deadline_report(load_verified(), today)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Fixed deadlines: {report['total_with_fixed_deadlines']}; upcoming: {report['upcoming_within_30_days']}; past: {report['past_deadline']}")


if __name__ == "__main__":
    main()
