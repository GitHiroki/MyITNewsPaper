# 🌅 Morning News Digest

- 毎朝7時にニュースを自動収集・AI要約して1ページのhtmlを作成するツール。
- 新聞のように朝読むことを想定している。

## 購読ソース

| カテゴリ | ソース |
|----------|--------|
| 技術 | Zenn トレンド, GitHub Trending, Hacker News, dev.to, gihyo.jp |
| AI・LLM | OpenAI Blog, Google Research Blog |
| セキュリティ | The Hacker News |
| 国内IT・ビジネス | ITmedia, 日経XTECH |

---

## 動作確認（手動実行）

Actionsの手動実行

## ローカルでのテスト実行

### 依存関係インストール
- `pip install -r requirements.txt`

### 環境変数をセット
- `export ANTHROPIC_API_KEY="..."`

### 実行
- `python main.py`

### 確認
- 同ディレクトリに`index.html`が出力されるので確認する

## カスタマイズ

### ソースを追加・削除する

1. `fetch_news.py`の`RSS_FEEDS`の追加
2. `summarize.py`のnews名の追加

### 通知時間を変える

`.github/workflows/morning_digest.yml`のcronを変更

```yaml
# 例：8時に変更（UTC 23:00）
- cron: "0 23 * * *"
```



## サマリ生成に失敗したとき

AI 要約が作れなくても、**タイトル一覧だけのページは毎朝公開する**方針です。
そのうえで、劣化は必ず通知で分かるようにしています。

| status | 意味 | Slack 通知 |
|---|---|---|
| `ok` | 全ソースで要約に成功 | 📰 通常の更新通知 |
| `degraded` | 一部のソースだけ失敗 | ⚠️ 成功/失敗の件数と失敗ソース名 |
| `fatal` | 回復不能なエラー（クレジット残高不足・認証エラー）で全滅 | ⚠️ 理由（例: APIクレジット残高不足）とページ/run URL |

- `fatal` のときは、1ソース目で打ち切って残りのソースは API を叩きません。
- `degraded` / `fatal` のときは `index.html` の先頭に警告バナーが出ます。
- Actions の Step Summary にソース別の OK / NG / SKIP 表が出ます。
- レート制限や 5xx などの一時的なエラーは、指数バックオフで最大3回まで再試行します。

### クレジット残高が切れたら

自動チャージは行いません。上記の `fatal` 通知を受け取ったら、
[Plans & Billing](https://console.anthropic.com/settings/billing) から**手動でチャージ**してください。
