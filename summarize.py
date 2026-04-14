"""
summarize.py
Claude API を使って記事を日本語サマリ化し、HTML を生成する
"""

import os
import json
import anthropic
from datetime import datetime, timezone, timedelta
from typing import Any

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

JST = timezone(timedelta(hours=9))

SYSTEM_PROMPT = """あなたは技術ニュースのキュレーターです。
記事タイトルとサマリを受け取り、JSON形式で返してください。

ルール:
- 1記事につき summary を1〜2文で日本語要約
- 英語タイトルは title_ja に日本語意訳
- 専門用語はそのまま使ってOK
- 「〜です」「〜ます」調で統一
- 重要度が低い記事は省いてよい

必ずJSON配列のみを返してください（前置き・コードブロック不要）:
[{"title_ja": "...", "url": "...", "summary": "..."}, ...]"""

GROUPS = {
    "🛠 技術": ["Zenn トレンド", "GitHub Trending", "Hacker News", "dev.to", "gihyo.jp"],
    "🤖 AI・LLM": ["OpenAI Blog", "Google Research Blog"],
    "🔒 セキュリティ": ["The Hacker News"],
    "📊 国内IT・ビジネス": ["ITmedia", "日経XTECH"],
}


def summarize_source(source_name: str, articles: list[dict[str, Any]]) -> list[dict]:
    """1ソース分の記事をClaude APIでサマリ化してリスト返却"""
    if not articles:
        return []

    # GitHub Trending はサマリ不要
    if source_name == "GitHub Trending":
        return [{"title_ja": a["title"], "url": a["url"], "summary": ""} for a in articles]

    articles_text = ""
    for i, a in enumerate(articles, 1):
        articles_text += f"{i}. タイトル: {a['title']}\n"
        if a["summary"]:
            articles_text += f"   概要: {a['summary'][:200]}\n"
        articles_text += f"   URL: {a['url']}\n\n"

    prompt = f"以下「{source_name}」の記事を要約してJSON配列で返してください。\n\n{articles_text}"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
            system=SYSTEM_PROMPT,
        )
        raw = message.content[0].text.strip()
        # コードブロックが含まれていたら除去
        if raw.startswith("```"):
            raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = "\n".join(raw.split("\n")[:-1])
        return json.loads(raw)
    except Exception as e:
        print(f"[WARN] {source_name} のサマリ生成失敗: {e}")
        return [{"title_ja": a["title"], "url": a["url"], "summary": ""} for a in articles]


def build_html(all_news: dict[str, list[dict[str, Any]]]) -> str:
    """全ソースのサマリを取得してHTMLページを生成する"""
    today = datetime.now(JST).strftime("%Y年%m月%d日")
    today_iso = datetime.now(JST).strftime("%Y-%m-%d")

    # 各ソースのサマリを収集
    summarized: dict[str, list[dict]] = {}
    for group_sources in GROUPS.values():
        for source_name in group_sources:
            if source_name in all_news:
                print(f"  サマリ生成中: {source_name}")
                summarized[source_name] = summarize_source(source_name, all_news[source_name])

    # HTML生成
    sections_html = ""
    for group_name, source_names in GROUPS.items():
        cards_html = ""
        for source_name in source_names:
            items = summarized.get(source_name, [])
            if not items:
                continue

            items_html = ""
            for item in items:
                summary_html = f'<p class="summary">{item["summary"]}</p>' if item.get("summary") else ""
                items_html += f"""
                <li>
                  <a href="{item['url']}" target="_blank" rel="noopener">{item['title_ja']}</a>
                  {summary_html}
                </li>"""

            cards_html += f"""
            <div class="card">
              <div class="card-header">{source_name}</div>
              <ul>{items_html}
              </ul>
            </div>"""

        if cards_html:
            sections_html += f"""
          <section>
            <h2>{group_name}</h2>
            <div class="cards">{cards_html}
            </div>
          </section>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>朝のニュースダイジェスト - {today}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;600;700&family=Noto+Sans+JP:wght@400;500&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #f5f0e8;
      --surface: #faf7f2;
      --surface2: #ede8de;
      --border: #c8bfb0;
      --border-dark: #8c7b6a;
      --accent: #c0622a;
      --text: #1a1410;
      --text-muted: #6b5e52;
      --radius: 3px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Noto Sans JP', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.7;
    }}
    header {{
      background: var(--surface);
      border-bottom: 3px double var(--border-dark);
      padding: 1.2rem 2rem;
      position: sticky;
      top: 0;
      z-index: 10;
    }}
    .header-inner {{
      max-width: 1100px;
      margin: 0 auto;
      display: flex;
      align-items: baseline;
      gap: 1rem;
    }}
    .logo {{
      font-family: 'EB Garamond', 'Noto Serif JP', serif;
      font-size: 1.6rem;
      font-weight: 600;
      color: var(--text);
      letter-spacing: 0.02em;
    }}
    .date-badge {{
      margin-left: auto;
      font-size: 0.72rem;
      color: var(--text-muted);
      border: 1px solid var(--border-dark);
      padding: 0.2rem 0.6rem;
      border-radius: 2px;
      letter-spacing: 0.06em;
      font-family: 'Noto Sans JP', sans-serif;
    }}
    main {{
      max-width: 1100px;
      margin: 0 auto;
      padding: 2.5rem 1.5rem 4rem;
    }}
    section {{
      margin-bottom: 3rem;
    }}
    h2 {{
      font-family: 'EB Garamond', 'Noto Serif JP', serif;
      font-size: 0.78rem;
      font-weight: 600;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 1rem;
      padding-bottom: 0.4rem;
      border-bottom: 2px solid var(--border-dark);
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--border-dark);
      border-radius: var(--radius);
      overflow: hidden;
      transition: box-shadow 0.2s, transform 0.2s;
    }}
    .card:hover {{
      box-shadow: 3px 3px 0 var(--border-dark);
      transform: translateY(-1px);
    }}
    .card-header {{
      font-family: 'Noto Sans JP', sans-serif;
      font-size: 0.68rem;
      font-weight: 500;
      color: var(--surface);
      background: var(--text);
      padding: 0.35rem 0.9rem;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }}
    ul {{
      list-style: none;
      padding: 0.25rem 0;
    }}
    li {{
      padding: 0.7rem 1rem;
      border-bottom: 1px solid var(--surface2);
    }}
    li:last-child {{ border-bottom: none; }}
    li a {{
      display: block;
      color: var(--text);
      text-decoration: none;
      font-family: 'Noto Serif JP', serif;
      font-size: 0.88rem;
      font-weight: 400;
      line-height: 1.55;
      margin-bottom: 0.2rem;
    }}
    li a:hover {{ color: var(--accent); text-decoration: underline; text-decoration-color: var(--accent); }}
    li a::before {{
      content: '— ';
      color: var(--accent);
    }}
    .summary {{
      font-size: 0.77rem;
      color: var(--text-muted);
      line-height: 1.65;
      margin-top: 0.15rem;
      font-family: 'Noto Sans JP', sans-serif;
    }}
    footer {{
      text-align: center;
      padding: 2rem;
      color: var(--text-muted);
      font-size: 0.78rem;
      border-top: 2px solid var(--border-dark);
      font-family: 'EB Garamond', serif;
      letter-spacing: 0.05em;
    }}
    @media (max-width: 600px) {{
      .cards {{ grid-template-columns: 1fr; }}
      header {{ padding: 1rem; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div class="logo">📰 Morning Digest</div>
      <div class="date-badge">{today_iso}</div>
    </div>
  </header>
  <main>{sections_html}
  </main>
  <footer>Generated by Claude API · {today}</footer>
</body>
</html>"""


if __name__ == "__main__":
    from fetch_news import fetch_all_news
    news = fetch_all_news()
    html = build_html(news)
    with open("digest.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("digest.html を出力しました")