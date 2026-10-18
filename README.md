# Hojokin Compass

登録不要・完全無料で、公的な補助金・助成金・給付金を探す静的Webサービスです。

- [トップページ](https://od-projects-jp.github.io/hojokin-compass/)
- [個人向け検索](https://od-projects-jp.github.io/hojokin-compass/individual.html)
- [法人・事業者向け検索](https://od-projects-jp.github.io/hojokin-compass/search.html)
- [確認済みの個人向け制度一覧](https://od-projects-jp.github.io/hojokin-compass/individual-directory.html)
- [プライバシーとブラウザ保存](https://od-projects-jp.github.io/hojokin-compass/privacy.html)

## 事業・開発方針

[2026-10-19決定の方針](docs/product-principles.md)に従い、会員登録・有料会員制・利用者個人情報のデータベースは設けません。検索条件とお気に入りは、ブラウザ内の `localStorage` に保存します。保存できない環境でも検索は利用できます。

収益化は将来の外部送客・アフィリエイトを中心に検討します。利用者情報をHojokin側で受け取らない設計を維持し、提携リンクを導入する場合は広告・提携関係を明示します。

詳細: [プライバシー・収益化の実装基準](docs/privacy-and-monetization-architecture.md)

## データ

- 個人向けは公式情報を確認した**47制度**を公開（2026-10-19時点）。うち**全国共通16制度**、残る31件は東京都・神奈川県・埼玉県の制度です。自治体独自制度の掲載地域は**3/47都道府県**にとどまります。
- 確認待ち候補は別ファイル・別画面で管理し、確認済み制度と混在させません。
- `collect_individual.py` が確認済み制度を公開JSONにまとめ、`individual_coverage.py`、`individual_deadlines.py`、`build_individual_directory.py` が掲載地域・期限・静的一覧を生成します。
- `audit_individual_links.py` が公式リンクの有効性を監査します。外部サイトの一時的なエラーで自動削除はしません。
- 法人・事業者向けはJグランツ等の公開情報を利用します。全制度の網羅性や申請資格は保証しません。

## 開発・テスト

- GitHub Pagesで静的サイトを配信します。
- GitHub Actionsでデータ更新、ユニットテスト、ブラウザ用JavaScriptの構文チェック、プライバシー制約チェックを実施します。
- ローカルテスト: `python -m unittest discover -s tests -v`、`node tests/browser-local-storage.test.js`、`node tests/privacy-guardrails.test.js`
- データ更新は `python collect_individual.py`、`python individual_coverage.py`、`python individual_deadlines.py`、`python build_individual_directory.py` の順に実行します。

## 注意

掲載情報は公的機関の情報に基づきますが、制度の受付状況・対象要件・申請期限・予算は変わる場合があります。必ず各制度の公式サイトをご確認ください。

外部ホスティング事業者による技術的なアクセス情報の処理を完全に制御できるわけではありません。Hojokin自身は会員情報を収集・保管しない方針です。
