# 🌅 Morning News Digest

毎朝7時にニュースを自動収集・AI要約して **GitHub Pages に HTML公開 → SlackにURLを通知** するツール。

## 購読ソース

| カテゴリ | ソース |
|----------|--------|
| 技術 | Zenn トレンド, GitHub Trending, Hacker News, dev.to |
| AI・LLM | Anthropic Blog, OpenAI Blog, Google AI Blog |
| 国内IT・ビジネス | ITmedia, TechCrunch Japan, 日経XTECH |

---

## セットアップ手順

### 1. このリポジトリをGitHubにpush

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_NAME/REPO_NAME.git
git push -u origin main
```

### 2. GitHub Pages を有効化

リポジトリの `Settings` → `Pages` →  
**Source: GitHub Actions** を選択して Save

（旧来の「Deploy from a branch」ではなく「GitHub Actions」を選ぶのがポイント）

### 3. Slack Incoming Webhook URLを取得

1. https://api.slack.com/apps にアクセス
2. 「Create New App」→「From scratch」
3. アプリ名を入力してワークスペースを選択
4. 左メニュー「Incoming Webhooks」を有効化
5. 「Add New Webhook to Workspace」でチャンネルを選択
6. 発行された Webhook URL をコピー

### 4. GitHub Secrets に登録

GitHubリポジトリの `Settings` → `Secrets and variables` → `Actions` で以下を登録：

| Secret名 | 値 |
|----------|----|
| `ANTHROPIC_API_KEY` | Anthropic APIキー（https://console.anthropic.com）|
| `SLACK_WEBHOOK_URL` | 手順3で取得したWebhook URL |

### 5. 動作確認（手動実行）

GitHubリポジトリの `Actions` タブ →「Morning News Digest」→「Run workflow」

---

## ローカルでのテスト実行

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数をセット
export ANTHROPIC_API_KEY="sk-ant-..."

# dry-run: Slack未送信・index.html をローカル出力
python main.py --dry-run

# ブラウザで確認
open index.html
```

---

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


