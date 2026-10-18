# 個人向け支援制度のデータ追加手順

## 収録範囲
- 公開対象: 公式サイトで申請者・対象地域・制度内容を確認した制度のみ
- 収集候補: 自動抽出しただけの制度は `individual_review.json` に分離し、公開しない
- 現在の自動収集元: 東京都の補助金CSV。全国網羅ではない

## 地域ごとの確認済みデータ
`public/data/individual_verified.json` は既存の東京都データとして維持する。
今後、地域別に `public/data/individual_verified/<region>.json` を追加できる。
各ファイルは以下の形式を使用する。

```json
{
  "subsidies": [
    {
      "title": "制度の正式名称",
      "description": "対象となる支援内容の概要",
      "area": "都道府県名または全国",
      "agency": "実施機関",
      "target": "直接申請できる対象者",
      "categories": ["子育て"],
      "source": "https://example.go.jp/official-program",
      "review_status": "公式情報確認済み",
      "verified_at": "2026-10-18"
    }
  ]
}
```

この例は**スキーマの説明用**であり、実在する制度として登録してはいけない。
`verified_at` は実際に公式情報を確認した日付を入力する。
公式サイトのURLが存在するだけでは募集継続・申請資格は確認できない。

## 自動化
1. `python -m unittest discover -s tests -v` で検証
2. `python collect_individual.py` で確認済みデータを公開JSONに統合し、東京都候補を別途収集
3. `python individual_coverage.py` で都道府県別の掲載件数を生成

全国対応には各自治体の公式情報源の調査・取得処理・制度単位の確認が別途必要。
