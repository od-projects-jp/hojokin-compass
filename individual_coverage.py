"""Generate transparent prefecture-level coverage from published verified records.

This is a coverage inventory, NOT a claim that all local programs are indexed.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

PREFECTURES = """北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県""".split()
PUBLIC = Path("public/data/individual.json")
OUTPUT = Path("public/data/individual_coverage.json")


def build_coverage(records):
    counts = {pref: 0 for pref in PREFECTURES}
    nationwide = 0
    for record in records:
        area = str(record.get("area") or "")
        if area == "全国":
            nationwide += 1
        else:
            for pref in PREFECTURES:
                if pref in area:
                    counts[pref] += 1
    return {
        "scope": "公開済みの確認済み制度の件数。自治体の制度網羅率ではありません。",
        "prefectures": counts,
        "nationwide": nationwide,
        "prefectures_with_records": sum(count > 0 for count in counts.values()),
        "total_prefectures": len(PREFECTURES),
    }


def main():
    data = json.loads(PUBLIC.read_text(encoding="utf-8"))
    records = data.get("subsidies")
    if not isinstance(records, list):
        raise ValueError("Public subsidies must be a list")
    report = build_coverage(records)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Coverage: {report['prefectures_with_records']}/47 prefectures with published records")


if __name__ == "__main__":
    main()
