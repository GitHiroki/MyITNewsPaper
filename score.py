"""
score.py
Jev（TypeSafe AI の System One）で記事ごとに「この読者が読む価値」をスコア化し、
ソースごとに上位だけを残す。

Jev は文章を書かず、状態を読んで score / choice / yes-no を返す判断専用モデル。
要約（Claude）の手前に置いて「何を要約するか」だけを決めさせる。

方針は summarize.py と同じく「失敗してもページは必ず出す」:
- TYPESAFE_API_KEY が無い → スコアリングせず、従来どおり先頭から KEEP 件
- 個別記事の判定に失敗 → その記事は元の並び順で後ろに回す
- 1ソースの全記事が失敗 → そのソースは従来どおり先頭から KEEP 件
"""

import html
import math
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

JEV_URL = os.environ.get("JEV_BASE_URL", "https://api.typesafe.ai/v1/systemone")
# 本番で挙動を固定したいときは JEV_MODEL=jev-1.13.0 のようにピン留めする
JEV_MODEL = os.environ.get("JEV_MODEL", "jev-latest")

KEEP_PER_SOURCE = int(os.environ.get("KEEP_PER_SOURCE", "5"))
MAX_WORKERS = 4
MAX_ATTEMPTS = 3
TIMEOUT_SEC = 30
# 選別全体にかける上限秒数。Jev が詰まってもジョブの timeout（15分）に食い込ませない。
# 超えた分の記事は「判定失敗」扱いになり、フォールバックで先頭から採用される
BUDGET_SEC = float(os.environ.get("JEV_BUDGET_SEC", "240"))

INTERESTS_FILE = Path(__file__).with_name("interests.md")

# Score の段階。index（0〜4）がそのままスコアになる
LEVELS = [
    "読む価値なし：関心領域と無関係、または宣伝・短信だけ",
    "ほぼ不要：関心領域に少しかかるが、得るものはほとんどない",
    "時間があれば：関心領域の話題だが、目新しさや実用性は普通",
    "読みたい：関心領域で、実務や個人開発にすぐ活かせそう",
    "必読：関心の中心にあり、今日いちばん読むべき記事",
]


def api_key() -> str | None:
    return os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")


def enabled() -> bool:
    return bool(api_key())


@dataclass
class ScoreReport:
    status: str = "disabled"            # disabled | ok | degraded
    scored: int = 0
    failed: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    # ソース名 -> [(score, title)]（残した記事のみ、ログ・Step Summary 用）
    picks: dict[str, list[tuple[float | None, str]]] = field(default_factory=dict)
    dropped: int = 0
    aborted: str = ""                   # 途中で打ち切った理由（時間切れ・認証エラー）


def _load_profile() -> str:
    try:
        return INTERESTS_FILE.read_text(encoding="utf-8")
    except OSError:
        return "Web系のバックエンドエンジニア。AIエージェントの実践的な活用、開発ツール、設計に関心がある。"


def _plain(text: str) -> str:
    """RSS の summary に混ざる HTML タグ・実体参照を落として1行にする"""
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


class _Abort:
    """期限切れや認証エラーで、残りの記事の判定をまとめて打ち切るためのフラグ"""

    def __init__(self, budget_sec: float):
        self.deadline = time.monotonic() + budget_sec
        self._event = threading.Event()
        self.reason = ""

    def stop(self, reason: str) -> None:
        if not self._event.is_set():
            self.reason = reason
            self._event.set()

    def check(self) -> bool:
        if not self._event.is_set() and time.monotonic() > self.deadline:
            self.stop(f"時間切れ（{BUDGET_SEC:.0f}秒）")
        return self._event.is_set()


def _build_request(article: dict[str, Any], profile: str) -> dict:
    # 日付や件数の比較は Jev が苦手なので渡さない。意味的な判断だけ任せる
    state = {
        "source": article.get("source", ""),
        "title": article.get("title", ""),
        "excerpt": _plain(article.get("summary") or "")[:500],
    }
    return {
        "model": JEV_MODEL,
        "state": state,
        "questions": {
            "value": {
                "type": "score",
                "instructions": {
                    "reader_profile": profile,
                    "question": "`reader_profile` の読者にとって、この記事を朝のダイジェストで読む価値はどのくらいか？",
                },
                "criteria": LEVELS,
            }
        },
    }


def _score_one(article: dict[str, Any], profile: str, key: str, abort: _Abort) -> tuple[float | None, dict]:
    """1記事を判定して (score, usage) を返す。失敗時は (None, {})"""
    body = _build_request(article, profile)
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    title = article.get("title", "")[:40]
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if abort.check():
            return None, {}
        last = attempt == MAX_ATTEMPTS
        try:
            res = requests.post(JEV_URL, json=body, headers=headers, timeout=TIMEOUT_SEC)
        except (requests.ConnectionError, requests.Timeout) as e:
            if not last:
                time.sleep(2.0 * 2 ** (attempt - 1))
                continue
            print(f"  [WARN] Jev 通信失敗: {title} — {type(e).__name__}")
            return None, {}

        # 混雑・一時障害はバックオフして再試行
        if (res.status_code in (429, 529) or res.status_code >= 500) and not last:
            time.sleep(2.0 * 2 ** (attempt - 1))
            continue
        # 401/422 などはリトライしても直らない
        if res.status_code != 200:
            print(f"  [WARN] Jev 判定失敗: {title} — HTTP {res.status_code}: {res.text[:200]}")
            # キーの誤りは全記事で同じ結果になるので、残りは呼ばずに打ち切る
            if res.status_code in (401, 403):
                abort.stop(f"認証エラー（HTTP {res.status_code}）")
            return None, {}
        try:
            data = res.json()
            score = float(data["answers"]["value"]["score"])
            if not math.isfinite(score):
                raise ValueError(score)
            return score, data.get("usage") or {}
        except Exception as e:
            print(f"  [WARN] Jev 応答のパース失敗: {title} — {type(e).__name__}: {res.text[:200]}")
            return None, {}
    return None, {}


def rank_and_trim(all_news: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, list[dict[str, Any]]], ScoreReport]:
    """ソースごとに Jev スコア順に並べ替え、上位 KEEP_PER_SOURCE 件だけ残す"""
    report = ScoreReport()
    key = api_key()

    if not key:
        trimmed = {name: arts[:KEEP_PER_SOURCE] for name, arts in all_news.items()}
        report.dropped = sum(len(a) for a in all_news.values()) - sum(len(a) for a in trimmed.values())
        return trimmed, report

    profile = _load_profile()
    jobs = [(name, i, a) for name, arts in all_news.items() for i, a in enumerate(arts)]
    abort = _Abort(BUDGET_SEC)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda j: _score_one(j[2], profile, key, abort), jobs))
    if abort.reason:
        report.aborted = abort.reason
        print(f"  [WARN] Jev の判定を打ち切りました: {abort.reason}")

    scores: dict[tuple[str, int], float | None] = {}
    for (name, i, _), (score, usage) in zip(jobs, results):
        scores[(name, i)] = score
        if score is None:
            report.failed += 1
        else:
            report.scored += 1
            report.input_tokens += usage.get("input_tokens", 0)
            report.output_tokens += usage.get("output_tokens", 0)

    trimmed: dict[str, list[dict[str, Any]]] = {}
    for name, arts in all_news.items():
        indexed = list(enumerate(arts))
        if all(scores[(name, i)] is None for i, _ in indexed):
            ranked = indexed  # 全滅したソースは従来どおり
        else:
            # スコア降順。判定失敗は後ろへ、同点は元の並び順
            ranked = sorted(
                indexed,
                key=lambda p: (scores[(name, p[0])] is None, -(scores[(name, p[0])] or 0), p[0]),
            )
        kept = ranked[:KEEP_PER_SOURCE]
        trimmed[name] = [a for _, a in kept]
        report.picks[name] = [(scores[(name, i)], a.get("title", "")) for i, a in kept]
        report.dropped += len(arts) - len(kept)

    report.status = "ok" if report.failed == 0 else "degraded"
    return trimmed, report


def print_picks(report: ScoreReport) -> None:
    """採用した記事とスコア、トークン使用量をログに出す（Step Summary を開かなくても確認できるように）"""
    print(f"   tokens: in {report.input_tokens:,} / out {report.output_tokens:,}")
    for name, picks in report.picks.items():
        print(f"   [{name}]")
        for sc, title in picks:
            s = "  —  " if sc is None else f"{sc:.2f}"
            print(f"     {s}  {title[:70]}")


def write_step_summary(report: ScoreReport) -> None:
    """Actions の画面に Jev の選別結果を出す（閾値やプロフィール調整用）"""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return

    lines = ["", "## 🧭 Jev 記事選別", ""]
    if report.status == "disabled":
        lines.append("TYPESAFE_API_KEY が未設定のため、スコアリングせず先頭から採用しました。")
    else:
        icon = "✅" if report.status == "ok" else "⚠️"
        lines += [
            f"{icon} 判定 {report.scored} 件 / 失敗 {report.failed} 件 / 除外 {report.dropped} 件"
            f"（tokens: in {report.input_tokens:,} / out {report.output_tokens:,}）",
        ]
        if report.aborted:
            lines += ["", f"途中で打ち切り：{report.aborted}。未判定の記事は元の並び順で扱いました。"]
        lines += [
            "",
            "| ソース | スコア | 採用した記事 |",
            "|---|---|---|",
        ]
        for name, picks in report.picks.items():
            for score, title in picks:
                s = "—" if score is None else f"{score:.2f}"
                lines.append(f"| {name} | {s} | {title.replace('|', '/')} |")

    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    # スモークテスト：各ソースの先頭2件だけ実際に採点して、生のスコアを表示する
    #   TYPESAFE_API_KEY=... python score.py
    from fetch_news import fetch_all_news

    if not enabled():
        raise SystemExit("TYPESAFE_API_KEY（または JEV_API_KEY）を設定してください")
    sample = {name: arts[:2] for name, arts in fetch_all_news().items()}
    _, rep = rank_and_trim(sample)
    print(f"status={rep.status} scored={rep.scored} failed={rep.failed} "
          f"tokens in={rep.input_tokens} out={rep.output_tokens} {rep.aborted}")
    for name, picks in rep.picks.items():
        for sc, t in picks:
            flag = "" if sc is None or 0 <= sc <= 4 else "  ← 0〜4 の範囲外"
            print(f"  [{name}] {sc} {t[:60]}{flag}")
