# TODO
- [ ] Djangoでアプリを作成する
- [ ] GitHubのmasterブランチを自動デプロイする
- [ ] GAEの環境変数が設定できるようにする
- [ ] cronの定期実行ができるようにする
- [ ] GCEにMySQLサーバーを立てる
- [ ] GCEのMySQLサーバーに接続してmigrationができるようにする
- [ ] SeleniumでHeadlessChromeを使えるようにする
- [ ] Djangoのクリーンアーキテクチャーを考える


# ライブラリ管理
- GAEがPipfileに対応していないのでrequirements.txtに書き出す
- `pipenv lock -r > requirements.txt`

# デプロイ
- `gcloud app deploy`
- `gcloud app deploy cron.yaml`
