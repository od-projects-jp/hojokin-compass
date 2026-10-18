
import csv
import io
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.opendata.metro.tokyo.lg.jp/zaimu/hojokin2026.csv"

PUBLIC_FILE = Path("public/data/individual.json")
REVIEW_FILE = Path("public/data/individual_review.json")

# 個人・世帯が対象である可能性を示す表現
PERSON_TERMS = [
    "個人", "都民", "住民", "世帯", "家庭",
    "保護者", "妊婦", "ひとり親",
    "住宅所有者", "住宅の所有者",
    "児童", "生徒", "学生", "高齢者", "障害者"
]

# 組織・施設への交付を示す表現
ORGANIZATION_TERMS = [
    "区市町村", "市区町村", "町村", "地方公共団体",
    "社会福祉法人", "医療法人", "学校法人",
    "特定非営利活動法人", "NPO法人",
    "民間団体", "事業者", "企業", "法人", "組合",
    "児童養護施設", "保育所", "保育施設",
    "学校", "施設", "団体", "事業所",
    "社会福祉協議会", "社会福祉施設"
]

# 個人向けとして扱うには追加確認が必要な表現
AMBIGUOUS_TERMS = [
    "個人事業主", "事業を営む個人",
    "里親", "養育家庭", "委託",
    "運営費", "整備費", "事業費"
]

CATEGORIES = {
    "住宅": ["住宅", "住まい", "耐震", "リフォーム", "家賃"],
    "子育て": ["子育て", "出産", "妊娠", "児童", "保育", "ひとり親"],
    "教育": ["教育", "奨学金", "授業料", "学生", "修学"],
    "医療": ["医療", "健康", "介護", "障害", "難病"],
    "仕事": ["就職", "求職", "雇用", "生活", "移住"],
    "省エネ": ["省エネ", "太陽光", "蓄電池", "断熱", "再エネ"]
}

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def fetch_rows():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "HojokinCompass/0.5"}
    )
    with urllib.request.urlopen(request, timeout=40) as response:
        raw = response.read()

    return list(csv.DictReader(io.StringIO(raw.decode("cp932"))))

def classify(row):
    title = clean(row.get("補助金名"))
    description = clean(row.get("補助金の概要"))
    target = clean(row.get("補助対象者"))

    if not title or not target:
        return None, None

    combined = title + " " + description

    categories = [
        category
        for category, words in CATEGORIES.items()
        if any(word in combined for word in words)
    ]

    item = {
        "title": title,
        "description": description,
        "area": "東京都",
        "agency": clean(row.get("所管部署")),
        "target": target,
        "eligible_costs": clean(row.get("補助対象経費")),
        "categories": categories,
        "source": clean(row.get("各局HPリンク")),
        "review_status": "要確認"
    }

    has_person = any(term in target for term in PERSON_TERMS)

    has_organization = any(
        term in target for term in ORGANIZATION_TERMS
    )

    has_ambiguous = any(
        term in combined + " " + target
        for term in AMBIGUOUS_TERMS
    )

    # 個人を示す記述がない制度は対象外
    if not has_person:
        return None, None

    # 組織向け・曖昧な制度は確認用に分離
    if has_organization or has_ambiguous:
        item["review_reason"] = (
            "組織向けまたは申請者区分が不明確"
        )
        return "review", item

    # 自動判定では申請資格を確定できないため、
    # こちらも確認用に分離する
    item["review_reason"] = "個人の直接申請可否が未確認"
    return "review", item

def save_json(path, items, generated_at):
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generated_at": generated_at,
        "source_name": "東京都 2026年補助金一覧",
        "source_url": URL,
        "total": len(items),
        "subsidies": items
    }

    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

def main():
    rows = fetch_rows()
    print(f"東京都の取得件数: {len(rows)}")

    public = []
    review = []
    seen = set()

    for row in rows:
        status, item = classify(row)
        if status is None:
            continue

        key = (item["title"], item["agency"])
        if key in seen:
            continue
        seen.add(key)

        if status == "public":
            public.append(item)
        else:
            review.append(item)

    generated_at = datetime.now(timezone.utc).isoformat()

    save_json(PUBLIC_FILE, public, generated_at)
    save_json(REVIEW_FILE, review, generated_at)

    print(f"公開対象: {len(public)}件")
    print(f"確認待ち: {len(review)}件")

    for item in review[:10]:
        print("確認候補:", item["title"])

if __name__ == "__main__":
    main()
