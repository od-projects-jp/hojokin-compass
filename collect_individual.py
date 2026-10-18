
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.opendata.metro.tokyo.lg.jp/zaimu/hojokin2026.csv"
OUTPUT = Path("public/data/individual.json")

# 個人が直接利用できる可能性を示す表現
PERSON_TERMS = [
    "個人", "都民", "住民", "世帯", "家庭",
    "保護者", "児童", "生徒", "学生",
    "妊婦", "ひとり親", "高齢者", "障害者",
    "住宅所有者", "住宅の所有者",
]

# 交付先が組織だけと判断できる表現
ORGANIZATION_TERMS = [
    "区市町村", "地方公共団体", "市区町村",
    "社会福祉法人", "医療法人",
    "学校法人", "特定非営利活動法人",
    "民間団体", "事業者", "企業",
    "法人", "組合",
]

CATEGORIES = {
    "住宅": ["住宅", "住まい", "耐震", "リフォーム", "家賃"],
    "子育て": ["子育て", "出産", "妊娠", "児童", "保育", "ひとり親"],
    "教育": ["教育", "奨学金", "授業料", "学生", "修学"],
    "医療": ["医療", "健康", "介護", "障害", "難病"],
    "仕事": ["就職", "求職", "雇用", "生活", "移住"],
    "省エネ": ["省エネ", "太陽光", "蓄電池", "断熱", "再エネ"],
}

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def fetch_rows():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "HojokinCompass/0.4"}
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read()

    text = raw.decode("cp932")
    return list(csv.DictReader(io.StringIO(text)))

def classify(row):
    title = clean(row.get("補助金名"))
    description = clean(row.get("補助金の概要"))
    target = clean(row.get("補助対象者"))

    if not title or not target:
        return None

    # 対象者欄に個人を示す表現が必要
    if not any(term in target for term in PERSON_TERMS):
        return None

    # 組織向けの可能性がある制度は、
    # 誤掲載を防ぐため自動公開しない
    if any(term in target for term in ORGANIZATION_TERMS):
        return None

    combined = title + " " + description
    categories = [
        category
        for category, words in CATEGORIES.items()
        if any(word in combined for word in words)
    ]

    return {
        "title": title,
        "description": description,
        "area": "東京都",
        "agency": clean(row.get("所管部署")),
        "target": target,
        "eligible_costs": clean(row.get("補助対象経費")),
        "categories": categories,
        "source": clean(row.get("各局HPリンク")),
        "review_status": "要確認",
    }

def main():
    rows = fetch_rows()
    print(f"東京都の取得件数: {len(rows)}")

    candidates = []
    seen = set()

    for row in rows:
        item = classify(row)
        if item is None:
            continue

        key = (item["title"], item["agency"])
        if key in seen:
            continue

        seen.add(key)
        candidates.append(item)

    # この段階では候補抽出であり、
    # 申請資格を保証するものではない
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_name": "東京都 2026年補助金一覧",
        "source_url": URL,
        "total": len(candidates),
        "subsidies": candidates,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"個人向け候補: {len(candidates)}件")
    print(f"保存先: {OUTPUT}")

    for item in candidates[:10]:
        print("候補:", item["title"], "|", item["target"][:80])

if __name__ == "__main__":
    main()
