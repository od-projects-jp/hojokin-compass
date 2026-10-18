# 全国の個人向け制度データ収集の拡張

## 目的
1件ずつコードに追加する方式から、**自治体の公式CSVを登録するだけで確認候補を収集**する方式に変更する。

## データの段階
1. **公式データソース**: `sources/individual_datasets.json` に公式CSV URL・公式紹介ページ・対象地域を登録
2. **確認待ち**: `collect_municipal.py` が `public/data/individual_candidates/<id>.json` を生成。自動で公開しない
3. **公式情報確認済み**: 申請者・対象地域・申請窓口・制度の現行性・公式ページを確認し `public/data/individual_verified/<region>.json` に追加
4. **公開**: `collect_individual.py` が確認済みのみ `public/data/individual.json` に統合

## 現在の公式ソース
- 愛知県「支援制度（給付金）情報」: https://www.pref.aichi.jp/opendata/support-info.html
- 小金井市「支援制度（給付金）情報」: https://catalog.data.metro.tokyo.lg.jp/dataset/t132101d0000000045
- 東京都補助金一覧（既存）: https://catalog.data.metro.tokyo.lg.jp/dataset/t000004d1800000019

デジタル庁の「自治体標準オープンデータセット」の**支援制度（給付金）情報**を優先して追加する。
https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test

## 自動実行・障害時
- GitHub Actions の日次処理と、収集コード・登録元変更時に実行
- CSVはUTF-8 / Shift-JISに対応し、最大5MB
- ソースごとの結果は `public/data/individual_collection_status.json` に記録
- ある自治体の失敗は他自治体の収集を妨げず、過去に成功した候補データを削除しない
- 見出し列が合わない場合はエラーとして記録し、架空の制度を作らない
- `review_priority` は確認作業の優先度にすぎず、受給資格を保証しない
- 候補件数は掲載件数・制度の網羅率ではない

## 新しい自治体を追加するには
`sources/individual_datasets.json` に公式CSVのエントリーを追加する。
安全のためダウンロード先のホスト名は `collect_municipal.py` の許可リストに登録する。
公式の紹介ページだけではなく、CSVの実URLと列構成を確認する。

## 確認作業ビュー
- [制度確認キュー](../individual-review.html) で確認待ち候補を検索・絞り込みできます。
- 表示するデータは未確認の収集候補です。掲載・申請資格の保証ではありません。
- 公式リンクで申請条件と最新年度を検証してから、確認済みJSONに反映してください。
- キューの生成は `build_individual_review_queue.py` によって日次収集時に実施します。
