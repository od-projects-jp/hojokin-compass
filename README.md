# Hojokin Compass — Data Collector v0.2

Jグランツ公開APIを利用したデータ収集の検証版。**この環境では外部APIとの実通信に成功していないため、取得件数は未検証です。**

## 実行

```bash
pip install -r requirements.txt
python collector.py --detail-limit 30
```

出力: `hojokin.sqlite`（制度・募集回・実行履歴）と `hojokin.report.json`（取得結果）。

## 仕様
- 複数キーワードで一覧を検索し、補助金IDで重複排除
- 詳細v2のworkflow（募集回）を別テーブルに保存
- 429・一時エラーに指数バックオフ
- APIへの過剰アクセスを避けるためリクエスト間隔を設定
- 実行履歴とエラーを保存

## 未対応・留意事項
- API接続テスト、レスポンス実データに基づく検証
- 全件網羅性の保証、自治体独自サイトの取り込み
- 公募要領からの条件抽出、厳密な受給額試算
- 同一制度の募集回ごとの期限・適格性の判定
- 公式API利用規約の遵守と出典表示が必要
- 公開サイトへの自動更新・デプロイ

公式仕様: https://developers.digital.go.jp/documents/jgrants/api/
