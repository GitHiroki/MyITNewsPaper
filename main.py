"""
main.py
朝のニュースダイジェスト - エントリーポイント

使い方:
  python main.py  # HTML生成（Slack通知はGitHub Actionsが行う）

サマリ生成に失敗してもページは必ず出力し、exit 0 で終了する。
そのかわり生成結果を GITHUB_OUTPUT / GITHUB_STEP_SUMMARY に書き出し、
ワークフロー側が劣化を検知して通知できるようにする。
"""

import os

from fetch_news import fetch_all_news
from summarize import DigestReport, build_html

OUTPUT_FILE = "index.html"


def _oneline(text: str) -> str:
    """GITHUB_OUTPUT に安全に書ける1行文字列にする"""
    return " ".join(text.split())


def write_github_output(report: DigestReport) -> None:
    """build ジョブの outputs 経由で deploy ジョブへ結果を渡す"""
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return

    failed = ", ".join(name for name, _ in report.failures)
    if report.skipped:
        failed = ", ".join(filter(None, [failed, f"(未処理: {', '.join(report.skipped)})"]))

    values = {
        "status": report.status,
        "reason": _oneline(report.reason),
        "ok_sources": str(report.ok_sources),
        "total_sources": str(report.total_sources),
        "failed_sources": _oneline(failed),
    }
    with open(path, "a", encoding="utf-8") as f:
        for key, value in values.items():
            f.write(f"{key}={value}\n")


def write_step_summary(report: DigestReport) -> None:
    """Actions の画面にソース別の OK/NG 表を出す"""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return

    icon = {"ok": "✅", "degraded": "⚠️", "fatal": "❌"}[report.status]
    reasons = dict(report.failures)

    lines = [
        "## 📰 Morning News Digest",
        "",
        f"{icon} **status: `{report.status}`** — サマリ生成成功 {report.ok_sources} / {report.total_sources} ソース",
        "",
    ]
    if report.reason:
        lines += [f"**理由**: {report.reason}", ""]

    lines += ["| ソース | 結果 | 理由 |", "|---|---|---|"]
    for name in report.source_order:
        if name in reasons:
            lines.append(f"| {name} | ❌ NG | {reasons[name]} |")
        elif name in report.skipped:
            lines.append(f"| {name} | ⏭ SKIP | 致命的エラーのため未実行 |")
        else:
            lines.append(f"| {name} | ✅ OK | |")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    print("📡 ニュース取得中...")
    all_news = fetch_all_news()
    total = sum(len(v) for v in all_news.values())
    print(f"✅ {len(all_news)}ソース / {total}記事 取得完了\n")

    print("🤖 Claude APIでサマリ生成・HTML構築中...")
    html, report = build_html(all_news)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"📄 {OUTPUT_FILE} を生成しました")

    print(
        f"📊 サマリ生成結果: status={report.status} "
        f"({report.ok_sources}/{report.total_sources} ソース成功)"
    )
    for name, reason in report.failures:
        print(f"   - {name}: {reason}")
    for name in report.skipped:
        print(f"   - {name}: 致命的エラーのため未実行")

    write_github_output(report)
    write_step_summary(report)


if __name__ == "__main__":
    main()
