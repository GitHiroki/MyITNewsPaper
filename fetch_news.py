"""
fetch_news.py
各ソースからニュース記事を取得する
"""

import feedparser
import requests
from datetime import datetime, timezone
from typing import Any

# ===== RSS フィード定義 =====
RSS_FEEDS = {
    "Zenn トレンド": "https://zenn.dev/feed",
    "Hacker News": "https://hnrss.org/frontpage?count=20",
    "dev.to": "https://dev.to/feed",
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Google Research Blog": "https://blog.google/technology/research/rss/",
    "ITmedia": "https://rss.itmedia.co.jp/rss/2.0/itmedia_all.xml",
    "日経XTECH": "https://xtech.nikkei.com/rss/index.rdf",
    "gihyo.jp": "https://gihyo.jp/feed/rss1",
}

MAX_ARTICLES_PER_SOURCE = 5  # ソースごとの最大記事数


def fetch_rss(name: str, url: str) -> list[dict[str, Any]]:
    """RSSフィードから記事を取得"""
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            articles.append({
                "source": name,
                "title": entry.get("title", "タイトルなし"),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", entry.get("description", ""))[:300],
                "published": entry.get("published", ""),
            })
        return articles
    except Exception as e:
        print(f"[WARN] {name} の取得失敗: {e}")
        return []


def fetch_github_trending() -> list[dict[str, Any]]:
    """GitHub Trending をスクレイピングで取得"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("https://github.com/trending", headers=headers, timeout=10)
        res.raise_for_status()

        from html.parser import HTMLParser

        class TrendingParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.repos = []
                self._in_h2 = False
                self._current_text = ""

            def handle_starttag(self, tag, attrs):
                attrs_dict = dict(attrs)
                if tag == "h2" and "lh-condensed" in attrs_dict.get("class", ""):
                    self._in_h2 = True
                    self._current_text = ""

            def handle_endtag(self, tag):
                if tag == "h2" and self._in_h2:
                    self._in_h2 = False
                    text = self._current_text.strip().replace("\n", "").replace(" ", "")
                    if "/" in text and len(self.repos) < MAX_ARTICLES_PER_SOURCE:
                        self.repos.append(text)

            def handle_data(self, data):
                if self._in_h2:
                    self._current_text += data

        parser = TrendingParser()
        parser.feed(res.text)

        articles = []
        for repo in parser.repos:
            articles.append({
                "source": "GitHub Trending",
                "title": repo,
                "url": f"https://github.com/{repo}",
                "summary": "",
                "published": "",
            })
        return articles
    except Exception as e:
        print(f"[WARN] GitHub Trending の取得失敗: {e}")
        return []


def fetch_all_news() -> dict[str, list[dict[str, Any]]]:
    """全ソースからニュースを取得してソース別に返す"""
    all_news: dict[str, list[dict[str, Any]]] = {}

    # GitHub Trending
    trending = fetch_github_trending()
    if trending:
        all_news["GitHub Trending"] = trending

    # RSS フィード
    for name, url in RSS_FEEDS.items():
        articles = fetch_rss(name, url)
        if articles:
            all_news[name] = articles

    return all_news


if __name__ == "__main__":
    import json
    news = fetch_all_news()
    for source, articles in news.items():
        print(f"\n=== {source} ({len(articles)}件) ===")
        for a in articles:
            print(f"  - {a['title'][:60]}")