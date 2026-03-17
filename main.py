"""
main.py
朝のニュースダイジェスト - エントリーポイント

使い方:
  python main.py             # HTML生成（Slack通知はGitHub Actionsが行う）
  python main.py --dry-run   # 同上・ローカル確認用
"""

import argparse
from fetch_news import fetch_all_news
from summarize import build_html

OUTPUT_FILE = "index.html"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="ローカル確認用（動作は通常実行と同じ）")
    args = parser.parse_args()

    print("📡 ニュース取得中...")
    all_news = fetch_all_news()
    total = sum(len(v) for v in all_news.values())
    print(f"✅ {len(all_news)}ソース / {total}記事 取得完了\n")

    print("🤖 Claude APIでサマリ生成・HTML構築中...")
    html = build_html(all_news)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 {OUTPUT_FILE} を生成しました")

    if args.dry_run:
        print(f"   ブラウザで確認: open {OUTPUT_FILE}")


if __name__ == "__main__":
    main()