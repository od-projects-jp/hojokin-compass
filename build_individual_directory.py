"""Create a crawlable, static directory from manually verified programs only."""
from collections import defaultdict
from html import escape
from pathlib import Path

from collect_individual import load_verified

OUTPUT = Path("individual-directory.html")
SITE = "https://od-projects-jp.github.io/hojokin-compass/"


def build_directory(records):
    groups = defaultdict(list)
    for item in records:
        groups[item["area"]].append(item)
    sections = []
    for area, items in sorted(groups.items(), key=lambda pair: (pair[0] != "全国", pair[0])):
        cards = []
        for item in sorted(items, key=lambda x: x["title"]):
            title = escape(item["title"])
            source = escape(item["source"], quote=True)
            summary = escape(item["description"])
            target = escape(item["target"])
            category = escape("・".join(item["categories"]))
            verified = escape(item["verified_at"])
            deadline = item.get("application_deadline")
            deadline_text = f'<p class="deadline">掲載年度の申請期限: {escape(deadline)}（最新の受付状況は公式サイトで確認）</p>' if deadline else ""
            cards.append(f'''<article class="item">
<h3>{title}</h3><p class="meta">{category} · 情報確認日 {verified}</p>
<p>{summary}</p><p><strong>対象:</strong> {target}</p>{deadline_text}
<p><a href="{source}" target="_blank" rel="noopener noreferrer">公式情報を確認 ↗</a></p>
</article>''')
        sections.append(f'<section><h2>{escape(area)}（{len(items)}件）</h2><div class="grid">{"".join(cards)}</div></section>')
    count = len(records)
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>確認済み支援制度一覧（{count}件） | Hojokin Compass</title>
<meta name="description" content="全国・東京都・神奈川県の公的支援制度を地域別に一覧化。公式情報を確認した{count}件の制度について対象者、内容、公式リンクを掲載。">
<link rel="canonical" href="{SITE}individual-directory.html">
<style>*{{box-sizing:border-box}}body{{margin:0;background:#f7f7f1;color:#193b31;font:16px/1.7 system-ui,-apple-system,sans-serif}}
header{{background:#fff;border-bottom:1px solid #dfe7de;padding:20px max(18px,calc((100vw - 1100px)/2))}}a{{color:#145a48}}main{{max-width:1100px;margin:auto;padding:30px 18px 70px}}
h1{{font-size:clamp(25px,4vw,36px)}}h2{{margin:34px 0 15px}}h3{{margin:0 0 10px;font-size:18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:14px}}
.item{{border:1px solid #dfe7de;border-radius:12px;background:#fff;padding:18px}}.item p{{margin:10px 0;font-size:14px}}
.meta{{color:#5c7168}}.deadline{{background:#fff3e5;padding:9px}}.notice{{padding:12px 15px;border-left:4px solid #64836a;background:#eaf1e9}}footer{{margin-top:30px;color:#62776b;font-size:13px}}
</style></head><body><header><a href="./">✧ Hojokin Compass</a>　<a href="individual.html">条件から探す</a></header>
<main><h1>確認済みの個人向け支援制度一覧</h1>
<p>公的機関の公式情報を確認した{count}件を地域別に掲載しています。全国・都道府県・市区町村の制度を混在して表示しているため、居住地などの対象要件を必ずご確認ください。</p>
<p class="notice">掲載件数は網羅率を示しません。申請資格・募集状況・予算残額・申請期限は公式サイトでご確認ください。</p>
{"".join(sections)}
<footer><a href="individual.html">地域・カテゴリから探す</a> · <a href="./">トップページ</a></footer>
</main></body></html>
'''


def main():
    records = load_verified()
    OUTPUT.write_text(build_directory(records), encoding="utf-8")
    print(f"Built crawlable directory for {len(records)} verified programs")


if __name__ == "__main__":
    main()
