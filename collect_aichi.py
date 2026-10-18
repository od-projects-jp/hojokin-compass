"""Import Aichi prefecture's official support-program CSV into a review-only queue.

This never publishes automatically. Field names can vary; retain source rows.
"""
import csv
import io
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.pref.aichi.jp/uploaded/life/631516_2906587_misc.csv"
LANDING = "https://www.pref.aichi.jp/opendata/support-info.html"
OUTPUT = Path("public/data/individual_review_aichi.json")


def decode_csv(raw):
    for encoding in ("utf-8-sig", "cp932", "utf-8"):
        try:
            return list(csv.DictReader(io.StringIO(raw.decode(encoding))))
        except UnicodeDecodeError:
            continue
    raise ValueError("Unsupported CSV encoding")


def clean(value):
    return " ".join(str(value or "").split())


def find_field(row, *names):
    for name in names:
        if clean(row.get(name)):
            return clean(row[name])
    return ""


def convert(rows):
    candidates = []
    for index, row in enumerate(rows, 1):
        title = find_field(row, "制度名", "支援制度名", "名称", "給付金名", "事業名")
        if not title:
            title = find_field(row, "タイトル")
        if not title:
            continue
        target = find_field(row, "対象者", "支援対象者", "給付対象者", "補助対象者")
        description = find_field(row, "制度概要", "概要", "内容", "支援内容", "説明")
        official = find_field(row, "URL", "関連URL", "詳細URL", "制度URL", "リンク")
        candidates.append({
            "title": title,
            "description": description,
            "area": "愛知県",
            "agency": find_field(row, "担当課", "所管課", "実施機関", "担当部署"),
            "target": target,
            "source": official or LANDING,
            "source_dataset": LANDING,
            "categories": [],
            "review_status": "要確認",
            "review_reason": "個人の直接申請可否・公式制度ページ・募集状況・カテゴリを未確認",
            "source_row": index,
            "raw_fields": {str(k): clean(v) for k, v in row.items() if k},
        })
    return candidates


def main():
    request = urllib.request.Request(URL, headers={"User-Agent": "HojokinCompass/1.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError("CSV exceeded size limit")
    rows = decode_csv(raw)
    if not rows:
        raise ValueError("Aichi source CSV is empty")
    candidates = convert(rows)
    if not candidates:
        raise ValueError("No recognized program titles; check source CSV columns")
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_name": "愛知県 支援制度（給付金）情報",
        "source_url": LANDING,
        "data_url": URL,
        "total": len(candidates),
        "subsidies": candidates,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Aichi: {len(candidates)} candidates for review (0 auto-published)")


if __name__ == "__main__":
    main()
