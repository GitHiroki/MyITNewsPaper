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


