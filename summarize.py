"""
summarize.py
Claude API を使って記事を日本語サマリ化し、HTML を生成する

サマリ生成に失敗してもページ自体は必ず生成する方針。
そのかわり失敗の内容を DigestReport にまとめて呼び出し側へ返し、
HTML の警告バナー / Slack 通知 / Step Summary で可視化できるようにする。
"""

import html as html_lib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

import anthropic

JST = timezone(timedelta(hours=9))

MAX_ATTEMPTS = 3        # 一時的なエラー時の最大試行回数（初回 + リトライ2回）
RETRY_BASE_WAIT = 2.0   # 指数バックオフの基準秒数

# サマリ生成はニュース見出しの要約・翻訳という定型タスクなので Haiku で足りる。
# Sonnet に戻したいときは CLAUDE_MODEL で上書きする。
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")

REQUIRED_KEYS = ("title_ja", "url", "summary")

_client: anthropic.Anthropic | None = None


class FatalSummaryError(Exception):
    """回復不能な API エラー。以降のソースを処理しても無駄なので打ち切る。"""

    def __init__(self, reason: str, detail: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def get_client() -> anthropic.Anthropic:
    """Anthropic クライアントを遅延初期化して返す"""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise FatalSummaryError("ANTHROPIC_API_KEY が未設定")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


SYSTEM_PROMPT = """あなたは技術ニュースのキュレーターです。
記事タイトルとサマリを受け取り、JSON形式で返してください。

ルール:
- 1記事につき summary を1〜2文で日本語要約
- 英語タイトルは title_ja に日本語意訳
- 専門用語はそのまま使ってOK
- 「〜です」「〜ます」調で統一
- 重要度が低い記事は省いてよい
- 各要素には必ず title_ja / url / summary の3キーをすべて含めること（省略・キー名の変更は不可）
- url は入力で与えられた URL をそのまま使うこと

必ずJSON配列のみを返してください（前置き・コードブロック不要）:
[{"title_ja": "...", "url": "...", "summary": "..."}, ...]"""

GITHUB_TRENDING_SYSTEM_PROMPT = """あなたは技術ニュースのキュレーターです。
GitHub Trendingのリポジトリ情報を受け取り、JSON形式で返してください。

ルール:
- 入力の title（リポジトリ名）は翻訳せず、そのまま title_ja に入れる
- description を自然な日本語に翻訳して summary に入れる
- description が空の場合は summary も空文字にする
- 各要素には必ず title_ja / url / summary の3キーをすべて含めること（title というキーは使わない）
- url は入力で与えられた URL をそのまま使うこと

必ずJSON配列のみを返してください（前置き・コードブロック不要）:
[{"title_ja": "...", "url": "...", "summary": "..."}, ...]"""

GROUPS = {
    "技術": ["Zenn トレンド", "GitHub Trending", "Hacker News", "dev.to", "gihyo.jp"],
    "AI・LLM": ["OpenAI Blog", "Google Research Blog"],
    "セキュリティ": ["The Hacker News"],
    "国内IT・ビジネス": ["ITmedia", "日経XTECH"],
}


@dataclass
class SourceResult:
    """1ソース分のサマリ生成結果"""
    source: str
    items: list[dict]
    ok: bool
    reason: str = ""


@dataclass
class DigestReport:
    """ダイジェスト生成全体の結果レポート"""
    total_sources: int = 0
    ok_sources: int = 0
    source_order: list[str] = field(default_factory=list)           # 処理した順のソース名
    failures: list[tuple[str, str]] = field(default_factory=list)   # (ソース名, 理由)
    skipped: list[str] = field(default_factory=list)                # 致命的エラーで未処理
    fatal_reason: str = ""

    @property
    def status(self) -> str:
        """ok | degraded | fatal"""
        if self.fatal_reason:
            return "fatal"
        if self.failures or self.skipped:
            return "degraded"
        return "ok"

    @property
    def reason(self) -> str:
        """通知やバナーに載せる代表的な理由（1行）"""
        if self.fatal_reason:
            return self.fatal_reason
        seen: list[str] = []
        for _, reason in self.failures:
            if reason not in seen:
                seen.append(reason)
        return " / ".join(seen)


def _fatal_reason(e: Exception) -> str | None:
    """回復不能なエラーなら日本語の理由を、そうでなければ None を返す"""
    msg = str(e).lower()
    if "credit balance" in msg:
        return "APIクレジット残高不足"
    if isinstance(e, anthropic.AuthenticationError):
        return "API認証エラー（APIキーが無効）"
    if isinstance(e, anthropic.PermissionDeniedError):
        return "APIアクセス権限エラー"
    if isinstance(e, anthropic.BadRequestError) and ("too low" in msg or "billing" in msg):
        return "APIクレジット残高不足"
    return None


def _is_transient(e: Exception) -> bool:
    """リトライで回復しうるエラーか"""
    if isinstance(e, (anthropic.RateLimitError, anthropic.APIConnectionError)):
        return True
    if isinstance(e, anthropic.APIStatusError):
        return e.status_code >= 500
    return False


def _call_claude(system: str, prompt: str, max_tokens: int) -> str:
    """Claude API を呼ぶ。致命的エラーは FatalSummaryError に変換し、一時的エラーはリトライする"""
    client = get_client()
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                system=system,
            )
            return message.content[0].text.strip()
        except Exception as e:
            reason = _fatal_reason(e)
            if reason:
                raise FatalSummaryError(reason, str(e)) from e
            if _is_transient(e) and attempt < MAX_ATTEMPTS:
                wait = RETRY_BASE_WAIT * (2 ** (attempt - 1))
                print(f"  [RETRY] 一時的なエラー（{attempt}/{MAX_ATTEMPTS}）{wait:.0f}秒後に再試行: {e}")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("unreachable")


def _parse_response(raw: str) -> list[dict]:
    """Claude の応答をパースして必須キーを検証する。不正なら例外を投げる"""
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
    if raw.endswith("```"):
        raw = "\n".join(raw.split("\n")[:-1])

    data = json.loads(raw)
    if not isinstance(data, list) or not data:
        raise ValueError("JSON配列ではないか、要素が空です")

    items = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("配列要素がオブジェクトではありません")
        missing = [k for k in REQUIRED_KEYS if k not in item]
        if missing:
            raise KeyError(f"必須キー欠落: {', '.join(missing)}")
        items.append({k: str(item[k]) for k in REQUIRED_KEYS})
    return items


def fallback_items(articles: list[dict[str, Any]], keep_summary: bool = False) -> list[dict]:
    """サマリなし（タイトルとURLのみ）のフォールバック"""
    return [
        {
            "title_ja": a["title"],
            "url": a["url"],
            "summary": a.get("summary", "") if keep_summary else "",
        }
        for a in articles
    ]


def summarize_source(source_name: str, articles: list[dict[str, Any]]) -> SourceResult:
    """1ソース分の記事を Claude API でサマリ化する

    致命的エラーは FatalSummaryError として呼び出し側に伝播させる。
    パース失敗などそのソース固有の問題は、フォールバックした SourceResult として返す。
    """
    if not articles:
        return SourceResult(source_name, [], ok=True)

    # GitHub Trending はdescriptionを日本語に翻訳して使う
    is_trending = source_name == "GitHub Trending"

    if is_trending:
        articles_text = ""
        for i, a in enumerate(articles, 1):
            articles_text += f"{i}. title: {a['title']}\n"
            articles_text += f"   description: {a.get('summary', '')}\n"
            articles_text += f"   URL: {a['url']}\n\n"
        prompt = f"以下のGitHub Trendingリポジトリ情報を翻訳してJSON配列で返してください。\n\n{articles_text}"
        system, max_tokens, label = GITHUB_TRENDING_SYSTEM_PROMPT, 1000, "翻訳"
    else:
        articles_text = ""
        for i, a in enumerate(articles, 1):
            articles_text += f"{i}. タイトル: {a['title']}\n"
            if a["summary"]:
                articles_text += f"   概要: {a['summary'][:200]}\n"
            articles_text += f"   URL: {a['url']}\n\n"
        prompt = f"以下「{source_name}」の記事を要約してJSON配列で返してください。\n\n{articles_text}"
        system, max_tokens, label = SYSTEM_PROMPT, 1500, "サマリ生成"

    try:
        raw = _call_claude(system, prompt, max_tokens)
    except FatalSummaryError:
        raise
    except Exception as e:
        reason = f"API呼び出し失敗（{type(e).__name__}）"
        print(f"[WARN] {source_name} の{label}失敗: {e}")
        return SourceResult(source_name, fallback_items(articles, keep_summary=is_trending), ok=False, reason=reason)

    try:
        return SourceResult(source_name, _parse_response(raw), ok=True)
    except Exception as e:
        reason = f"応答のパース失敗（{type(e).__name__}）"
        print(f"[WARN] {source_name} の応答パース失敗: {e}")
        return SourceResult(source_name, fallback_items(articles, keep_summary=is_trending), ok=False, reason=reason)


# デジタル庁デザインシステム（DADS）のスタイル
# 色・角丸・フォントの値は @digital-go-jp/design-tokens v2.0.1 (dist/tokens.css) より
# https://design.digital.go.jp/dads/
STYLE = """
    :root {
      --color-key-50: #e8f1fe;
      --color-key-100: #d9e6ff;
      --color-key-200: #c5d7fb;
      --color-key-900: #0017c1;   /* キーカラー */
      --color-key-1000: #00118f;
      --color-key-1200: #000060;
      --color-white: #ffffff;
      --color-gray-50: #f2f2f2;
      --color-gray-100: #e6e6e6;
      --color-gray-200: #cccccc;
      --color-gray-536: #767676;  /* 4.5:1 を満たす最も薄いグレー */
      --color-gray-700: #4d4d4d;
      --color-gray-800: #333333;
      --color-gray-900: #1a1a1a;  /* 本文色 */
      --color-warning-1: #b78f00;
      --color-warning-bg: #fbf5e0;
      --color-success-1: #259d63;
      --color-focus-ring: #ffc700;
      --radius-4: 4px;
      --radius-8: 8px;
      --font-sans: 'Noto Sans JP', -apple-system, BlinkMacSystemFont, 'Hiragino Sans', sans-serif;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      font-size: 16px;
      line-height: 1.7;
      color: var(--color-gray-900);
      background: var(--color-gray-50);
      -webkit-font-smoothing: antialiased;
    }
    /* DADS のフォーカスインジケーター（黒アウトライン + 黄色リング） */
    a:focus-visible, .skip-link:focus {
      outline: 2px solid var(--color-gray-900);
      outline-offset: 0;
      box-shadow: 0 0 0 4px var(--color-focus-ring);
      border-radius: var(--radius-4);
    }
    .skip-link {
      position: absolute; left: 16px; top: -48px;
      background: var(--color-white); color: var(--color-key-900);
      padding: 8px 16px; border-radius: var(--radius-4); font-weight: 700;
      transition: top .15s;
    }
    .skip-link:focus { top: 8px; z-index: 100; }
    header {
      background: var(--color-white);
      border-bottom: 1px solid var(--color-gray-200);
      position: sticky; top: 0; z-index: 10;
    }
    .header-inner {
      max-width: 1120px; margin: 0 auto;
      padding: 16px 24px;
      display: flex; align-items: center; gap: 16px;
    }
    .logo {
      font-size: 20px; font-weight: 700; letter-spacing: .02em;
      color: var(--color-key-900);
    }
    .date-badge {
      margin-left: auto;
      font-size: 14px; font-weight: 700;
      color: var(--color-key-1000); background: var(--color-key-50);
      border: 1px solid var(--color-key-200);
      padding: 2px 12px; border-radius: 999px;
    }
    main { max-width: 1120px; margin: 0 auto; padding: 32px 24px 64px; }
    .lede { font-size: 14px; color: var(--color-gray-700); margin-bottom: 24px; }
    .lede .status {
      display: inline-flex; align-items: center; gap: 6px;
      font-weight: 700; color: var(--color-success-1);
    }
    section { margin-bottom: 40px; }
    h2 {
      font-size: 22px; font-weight: 700; line-height: 1.5;
      padding-left: 12px; margin-bottom: 16px;
      border-left: 4px solid var(--color-key-900);
      display: flex; align-items: baseline; gap: 12px;
    }
    h2 .count { font-size: 14px; font-weight: 400; color: var(--color-gray-536); }
    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
    }
    .card {
      background: var(--color-white);
      border: 1px solid var(--color-gray-200);
      border-radius: var(--radius-8);
      overflow: hidden;
    }
    .card-header {
      font-size: 16px; font-weight: 700;
      color: var(--color-key-1000); background: var(--color-key-50);
      border-bottom: 1px solid var(--color-key-100);
      padding: 8px 16px;
    }
    ul { list-style: none; }
    li { border-bottom: 1px solid var(--color-gray-100); }
    li:last-child { border-bottom: none; }
    li a {
      display: block; padding: 12px 16px 4px;
      font-size: 17px; font-weight: 700; line-height: 1.5;
      color: var(--color-key-900);
      text-decoration: underline; text-underline-offset: 3px;
    }
    li a:hover { color: var(--color-key-1000); background: var(--color-key-50); }
    li a:visited { color: var(--color-key-1200); }
    .summary {
      font-size: 14px; line-height: 1.7; color: var(--color-gray-700);
      padding: 0 16px 12px;
    }
    /* 劣化時の警告バナー（DADS の Notification Banner 相当） */
    .notice {
      background: var(--color-warning-bg);
      border: 2px solid var(--color-warning-1);
      border-radius: var(--radius-8);
      padding: 16px; margin-bottom: 24px;
      display: flex; gap: 12px; align-items: flex-start;
    }
    .notice-icon {
      flex: none; width: 24px; height: 24px; border-radius: 50%;
      background: var(--color-warning-1); color: var(--color-white);
      font-size: 15px; font-weight: 700; display: grid; place-items: center;
      margin-top: 2px;
    }
    .notice strong { display: block; font-size: 18px; line-height: 1.5; }
    .notice p { font-size: 14px; color: var(--color-gray-800); }
    footer {
      background: var(--color-gray-900); color: var(--color-white);
      font-size: 14px; padding: 24px;
    }
    .footer-inner {
      max-width: 1120px; margin: 0 auto;
      display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline;
    }
    footer .muted { color: var(--color-gray-200); }
    @media (max-width: 600px) {
      .cards { grid-template-columns: 1fr; }
      .header-inner { padding: 12px 16px; }
      .logo { font-size: 17px; }
      main { padding: 24px 16px 48px; }
      h2 { font-size: 20px; }
    }
"""


def _banner_html(report: "DigestReport") -> str:
    """劣化時に HTML 先頭へ出す警告バナー"""
    if report.status == "ok":
        return ""
    if report.status == "fatal":
        headline = "本日は AI 要約を生成できませんでした"
    else:
        headline = "本日は一部のソースで AI 要約を生成できませんでした"
    reason = html_lib.escape(report.reason or "原因不明")
    counts = f"要約成功 {report.ok_sources} / {report.total_sources} ソース"
    return f'''
    <div class="notice" role="status">
      <span class="notice-icon" aria-hidden="true">!</span>
      <div>
        <strong>{headline}</strong>
        <p>理由: {reason}（{counts}）。要約できなかったソースは、記事のタイトルとリンクのみ掲載しています。</p>
      </div>
    </div>'''


def build_html(all_news: dict[str, list[dict[str, Any]]]) -> tuple[str, DigestReport]:
    """全ソースのサマリを取得してHTMLページと結果レポートを返す

    サマリ生成に失敗してもページは必ず生成する。
    致命的エラーが起きた時点で以降のソースは API を叩かず打ち切る。
    """
    today = datetime.now(JST).strftime("%Y年%m月%d日")
    today_iso = datetime.now(JST).strftime("%Y-%m-%d")

    # 各ソースのサマリを収集
    report = DigestReport()
    summarized: dict[str, list[dict]] = {}
    for group_sources in GROUPS.values():
        for source_name in group_sources:
            if source_name not in all_news:
                continue
            articles = all_news[source_name]
            report.total_sources += 1
            report.source_order.append(source_name)

            # 致命的エラー発生後は API を叩かずフォールバックのみ
            if report.fatal_reason:
                summarized[source_name] = fallback_items(articles)
                report.skipped.append(source_name)
                continue

            print(f"  サマリ生成中: {source_name}")
            try:
                result = summarize_source(source_name, articles)
            except FatalSummaryError as e:
                print(f"[FATAL] {source_name} で回復不能なエラー: {e.reason} — 以降のソースを打ち切ります")
                if e.detail:
                    print(f"        詳細: {e.detail}")
                report.fatal_reason = e.reason
                report.failures.append((source_name, e.reason))
                summarized[source_name] = fallback_items(articles)
                continue

            summarized[source_name] = result.items
            if result.ok:
                report.ok_sources += 1
            else:
                report.failures.append((source_name, result.reason))

    banner_html = _banner_html(report)

    # HTML生成
    total_items = 0
    sections_html = ""
    for group_name, source_names in GROUPS.items():
        cards_html = ""
        group_items = 0
        for source_name in source_names:
            items = summarized.get(source_name, [])
            if not items:
                continue
            group_items += len(items)

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
            total_items += group_items
            sections_html += f"""
          <section>
            <h2>{group_name}<span class="count">{group_items}件</span></h2>
            <div class="cards">{cards_html}
            </div>
          </section>"""

    status_html = '<span class="status">● 全ソース要約済み</span>' if report.status == "ok" else ""
    lede_html = (
        f'<p class="lede">{report.total_sources}ソースから {total_items} 件をお届けします。'
        f'{status_html}</p>'
    )

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>朝のニュースダイジェスト - {today}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">
  <style>{STYLE}</style>
</head>
<body>
  <a class="skip-link" href="#main">本文へスキップ</a>
  <header>
    <div class="header-inner">
      <div class="logo">Morning Digest</div>
      <div class="date-badge">{today_iso}</div>
    </div>
  </header>
  <main id="main">{banner_html}
    {lede_html}{sections_html}
  </main>
  <footer>
    <div class="footer-inner">
      <span>Morning News Digest</span>
      <span class="muted">Generated by Claude API · {today}</span>
    </div>
  </footer>
</body>
</html>"""

    return html, report


if __name__ == "__main__":
    from fetch_news import fetch_all_news
    news = fetch_all_news()
    html, report = build_html(news)
    with open("digest.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"digest.html を出力しました (status={report.status}, {report.ok_sources}/{report.total_sources})")