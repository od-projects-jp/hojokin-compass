
import csv
import io
import urllib.request

URL = "https://www.opendata.metro.tokyo.lg.jp/zaimu/hojokin2026.csv"

def main():
    print("東京都の補助金データを取得します")

    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "HojokinCompass/0.4"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()

    print(f"取得サイズ: {len(raw):,} bytes")

    text = None
    for encoding in ("utf-8-sig", "cp932"):
        try:
            text = raw.decode(encoding)
            print(f"文字コード: {encoding}")
            break
        except UnicodeDecodeError:
            continue

    if text is None:
        raise ValueError("文字コードを判定できませんでした")

    rows = list(csv.DictReader(io.StringIO(text)))

    if not rows:
        raise ValueError("CSVにデータがありません")

    print(f"取得件数: {len(rows)}")
    print("データ項目:")
    for column in rows[0].keys():
        print(" -", column)

    print("先頭3件の制度名候補:")
    for row in rows[:3]:
        print(row)

if __name__ == "__main__":
    main()
