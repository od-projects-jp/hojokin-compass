"""Build an actionable review queue without treating candidates as verified."""
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from collect_individual import load_verified

CANDIDATES_DIR = Path("public/data/individual_candidates")
OUTPUT = Path("public/data/individual_review_queue.json")


def canonical_url(url):
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    return (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"))


def build_queue(candidate_sets, verified):
    verified_urls = {canonical_url(x.get("source")) for x in verified if x.get("source")}
    verified_names = {(x.get("area", ""), x.get("title", "")) for x in verified}
    queue = []
    seen = set()
    for dataset in candidate_sets:
        for item in dataset.get("subsidies", []):
            url = canonical_url(item.get("source"))
            key = (item.get("source_id", ""), item.get("title", ""), url)
            if key in seen:
                continue
            seen.add(key)
            if (item.get("area", ""), item.get("title", "")) in verified_names:
                continue
            # Same official program page may list multiple distinct benefits.
            # Mark as potentially covered; don't automatically discard.
            already_covered_url = bool(url and url in verified_urls)
            candidate = {k: item.get(k) for k in (
                "title", "area", "source_id", "source", "target",
                "review_priority", "past_year_in_title", "possible_business_only"
            )}
            candidate["potentially_covered"] = already_covered_url
            queue.append(candidate)
    queue.sort(key=lambda x: (
        x["review_priority"] != "高",
        x["possible_business_only"] is True,
        x["potentially_covered"] is True,
        x["title"] or "",
    ))
    return queue


def main():
    datasets = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CANDIDATES_DIR.glob("*.json"))]
    queue = build_queue(datasets, load_verified())
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": len(queue),
        "high_priority": sum(x["review_priority"] == "高" for x in queue),
        "potentially_covered": sum(x["potentially_covered"] for x in queue),
        "notice": "内部確認用候補。申請可能な制度や公開件数ではありません。",
        "candidates": queue,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Review queue: {len(queue)} candidates; {payload['high_priority']} high priority")


if __name__ == "__main__":
    main()
