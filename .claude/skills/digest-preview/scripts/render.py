"""サンプルデータで digest ページの HTML を描画する（Claude API は呼ばない）

summarize.build_html をそのまま使い、summarize_source だけを差し替える。
テンプレートは本番と同一なので、ここで見えた崩れは本番でも起きる。

使い方:
    python3 render.py <出力先.html> [--state ok|degraded|fatal]
"""

import argparse
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """summarize.py のあるディレクトリを上へ辿って探す"""
    for parent in Path(__file__).resolve().parents:
        if (parent / "summarize.py").exists():
            return parent
    raise SystemExit("summarize.py が見つかりません（リポジトリ内で実行してください）")


sys.path.insert(0, str(find_repo_root()))

import summarize  # noqa: E402

from sample_data import SAMPLE  # noqa: E402

# degraded のときに失敗させるソース
DEGRADED_SOURCES = ("Hacker News", "dev.to")


def check_sample_covers_groups() -> None:
    """サンプルデータと summarize.GROUPS のズレを検出する

    ソースを追加・改名したときに気付けないと、そのソースだけプレビューに
    出てこない（あるいは KeyError で落ちる）ので、先に突き合わせておく。
    """
    known = {name for names in summarize.GROUPS.values() for name in names}
    missing = known - set(SAMPLE)
    extra = set(SAMPLE) - known
    problems = []
    if missing:
        problems.append(f"sample_data.py に無いソース: {sorted(missing)}")
    if extra:
        problems.append(f"summarize.GROUPS に無いソース: {sorted(extra)}")
    if problems:
        raise SystemExit(
            "サンプルデータと summarize.GROUPS がずれています。\n  "
            + "\n  ".join(problems)
            + "\nscripts/sample_data.py を更新してください。"
        )


def make_summarizer(state: str):
    def summarize_source(source_name, articles):
        if state == "fatal":
            raise summarize.FatalSummaryError("APIクレジット残高不足")
        if state == "degraded" and source_name in DEGRADED_SOURCES:
            return summarize.SourceResult(
                source=source_name,
                items=summarize.fallback_items(articles),
                ok=False,
                reason="APIレート制限",
            )
        return summarize.SourceResult(source=source_name, items=SAMPLE[source_name], ok=True)

    return summarize_source


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="出力する HTML のパス")
    parser.add_argument(
        "--state",
        choices=("ok", "degraded", "fatal"),
        default="ok",
        help="要約の成否。degraded は一部失敗、fatal は全滅（既定: ok）",
    )
    args = parser.parse_args()

    check_sample_covers_groups()
    summarize.summarize_source = make_summarizer(args.state)

    all_news = {
        name: [{"title": item["title_ja"], "url": item["url"]} for item in items]
        for name, items in SAMPLE.items()
    }
    html, report = summarize.build_html(all_news)
    Path(args.output).write_text(html, encoding="utf-8")
    print(f"{args.output} (status={report.status})")


if __name__ == "__main__":
    main()
