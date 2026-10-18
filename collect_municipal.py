"""Official municipal support-data importer: candidate queue only, never auto-publish.

Add new official CSV datasets to sources/individual_datasets.json.
Each source fails independently; a failure never deletes its last successful output.
"""
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

REGISTRY = Path("sources/individual_datasets.json")
OUTPUT_DIR = Path("public/data/individual_candidates")
REPORT = Path("public/data/individual_collection_status.json")
MAX_BYTES = 5_000_000
ALLOWED_HOSTS = {"www.pref.aichi.jp", "www.opendata.metro.tokyo.lg.jp", "www2.wagmap.jp"}

TITLE_FIELDS = ("制度名", "支援制度名", "名称", "給付金名", "事業名", "タイトル", "支援制度名称", "支援制度名（正式名称）", "タイトル（制度名）")
TARGET_FIELDS = ("対象者", "支援対象者", "給付対象者", "補助対象者", "対象")
DESCRIPTION_FIELDS = ("制度概要", "概要", "内容", "支援内容", "説明", "制度内容")
LINK_FIELDS = ("URL", "関連URL", "詳細URL", "制度URL", "リンク", "詳細情報URL", "参照URL", "制度詳細URL", "参照先URL")
AGENCY_FIELDS = ("担当課", "所管課", "実施機関", "担当部署", "実施主体", "担当部局", "制度所管組織")
PERSON_HINTS = ("個人", "住民", "市民", "県民", "世帯", "保護者", "子ども", "児童", "妊婦", "学生", "高齢者", "ひとり親")
BUSINESS_HINTS = ("法人", "事業者", "企業", "事業所", "組合", "団体")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def get_field(row, names):
    # Strip whitespace and BOM, but do not guess from unrelated columns.
    normalized = {clean(key).replace("\ufeff", ""): clean(value) for key, value in row.items() if key}
    for name in names:
        if normalized.get(name):
            return normalized[name]
    return ""


def parse_csv(raw):
    for encoding in ("utf-8-sig", "cp932", "utf-8"):
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        rows = list(csv.DictReader(io.StringIO(decoded)))
        if not rows:
            raise ValueError("Source contains no CSV rows")
        return rows
    raise ValueError("CSV encoding not recognized")


def validate_source(source):
    if not re.fullmatch(r"[a-z0-9_-]{2,50}", source["id"]):
        raise ValueError("Invalid source ID")
    for key in ("dataset_url", "landing_url"):
        url = urlparse(source[key])
        if url.scheme != "https" or url.hostname not in ALLOWED_HOSTS and key == "dataset_url":
            raise ValueError(f"Unapproved dataset URL: {key}")
        if key == "landing_url" and (url.scheme != "https" or not url.hostname):
            raise ValueError("Landing URL must be HTTPS")


def normalize(rows, source):
    candidates = []
    seen = set()
    for index, row in enumerate(rows, 1):
        title = get_field(row, TITLE_FIELDS)
        if not title:
            continue
        target = get_field(row, TARGET_FIELDS)
        description = get_field(row, DESCRIPTION_FIELDS)
        url = get_field(row, LINK_FIELDS)
        if not url.startswith("https://"):
            url = source["landing_url"]
        personal = any(word in target for word in PERSON_HINTS)
        business = any(word in target for word in BUSINESS_HINTS)
        priority = "高" if personal and not business and url != source["landing_url"] else "通常"
        old_year_in_title = bool(re.search(r"(?:令和[1-7]年度|202[0-5]年度|202[0-5]年)", title))
        if old_year_in_title:
            priority = "要更新確認"
        key = (title, target)
        if key in seen:
            continue
        seen.add(key)
        candidates.append({
            "title": title,
            "description": description,
            "area": source["area"],
            "agency": get_field(row, AGENCY_FIELDS),
            "target": target,
            "source": url,
            "source_dataset": source["landing_url"],
            "source_id": source["id"],
            "source_row": index,
            "categories": [],
            "review_status": "要確認",
            "review_priority": priority,
            "past_year_in_title": old_year_in_title,
            "possible_business_only": business and not personal,
            "review_reason": "申請資格・公式制度ページ・募集状況の確認が必要",
            "source_note": source.get("source_note", ""),
        })
    if not candidates:
        raise ValueError("No matching title field; columns: " + ", ".join(str(x) for x in rows[0]))
    return sorted(candidates, key=lambda item: (item["review_priority"] != "高", item["title"]))


def collect_one(source, opener=urllib.request.urlopen):
    validate_source(source)
    request = urllib.request.Request(source["dataset_url"], headers={"User-Agent": "HojokinCompass/1.0"})
    with opener(request, timeout=35) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Source exceeds maximum CSV size")
    rows = parse_csv(raw)
    candidates = normalize(rows, source)
    return {"source_id": source["id"], "source_name": source["name"],
            "source_url": source["landing_url"], "total": len(candidates),
            "subsidies": candidates}


def run():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    sources = [s for s in registry["sources"] if s.get("enabled", True)]
    if not sources:
        raise ValueError("No enabled sources")
    ids = [s["id"] for s in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source IDs")
    results = []
    for source in sources:
        try:
            payload = collect_one(source)
            target = OUTPUT_DIR / (source["id"] + ".json")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            results.append({"source_id": source["id"], "status": "ok",
                            "candidate_count": payload["total"],
                            "high_priority_count": sum(x["review_priority"] == "高" for x in payload["subsidies"]),
                            "possible_business_only_count": sum(x["possible_business_only"] for x in payload["subsidies"]),
                            "output": str(target)})
            print(source["id"], "candidates:", payload["total"])
        except Exception as exc:
            # Keep the last good candidate snapshot, if one exists.
            results.append({"source_id": source["id"], "status": "error", "error": str(exc)[:350]})
            print(source["id"], "failed:", exc)
    status = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "source_count": len(sources), "success_count": sum(x["status"] == "ok" for x in results),
              "candidate_count_this_run": sum(x.get("candidate_count", 0) for x in results),
              "high_priority_count_this_run": sum(x.get("high_priority_count", 0) for x in results),
              "sources": results, "notice": "候補数であり、公開済み・申請可能な制度数ではありません。"}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if status["success_count"] == 0:
        raise RuntimeError("All municipal candidate sources failed")
    return status


if __name__ == "__main__":
    run()
