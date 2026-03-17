# 🌅 Morning News Digest

毎朝7時にニュースを自動収集・AI要約して **GitHub Pages に HTML公開 → SlackにURLを通知** するツール。

## 購読ソース

| カテゴリ | ソース |
|----------|--------|
| 技術 | Zenn トレンド, GitHub Trending, Hacker News, dev.to |
| AI・LLM | OpenAI Blog, Google AI Blog |
| 国内IT・ビジネス | ITmedia, 日経XTECH |

---

## 動作確認（手動実行）

Actionsの手動実行

## ローカルでのテスト実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数をセット
export ANTHROPIC_API_KEY="..."

# dry-run: Slack未送信・index.html をローカル出力
python main.py --dry-run

# ブラウザで確認
open index.html
```

## カスタマイズ

### ソースを追加・削除する

`fetch_news.py` の `RSS_FEEDS` 辞書を編集するだけでOK：

```python
RSS_FEEDS = {
    "Zenn トレンド": "https://zenn.dev/feed",
    # 追加例
    "Qiita トレンド": "https://qiita.com/popular-items/feed",
}
```

### 通知時間を変える

`.github/workflows/morning_digest.yml` の cron を変更：

```yaml
# 例：8時に変更（UTC 23:00）
- cron: "0 23 * * *"
```


