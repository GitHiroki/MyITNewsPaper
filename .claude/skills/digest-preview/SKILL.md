---
name: digest-preview
description: MyITNewsPaper の digest ページ（summarize.py が出力する index.html）の見た目を、Claude API を叩かずにサンプルデータで描画し、PC・スマホのスクリーンショットと変更前後の比較画像を作る。summarize.py の CSS や HTML テンプレート、build_html / _banner_html を触ったとき、デザインシステムやトークンを適用するとき、「見た目を確認したい」「どう見える？」「スクショで見せて」「崩れてない？」と言われたときは必ずこの手順を使う。コードを読んで「たぶん大丈夫」と答えるのではなく、実際に描画して目で確かめるためのもの。
---

# digest ページのデザインプレビュー

`summarize.py` のテンプレートは本番の GitHub Actions でしか実行されないため、
CSS をいじっても手元では何も確認できない。このスキルは `summarize.build_html` を
**ダミーデータで直接呼び**、実際のブラウザで描画してスクショを撮る。

テンプレートは本番と同一のものを通すので、ここで見えた崩れは本番でも起きるし、
ここで直っていれば本番でも直っている。

## 準備（初回のみ）

```bash
pip install playwright pillow anthropic
```

`anthropic` は `summarize.py` の import を通すためだけに必要で、API は呼ばない。
Playwright のブラウザは環境に同梱されているものを使うので `playwright install` は不要。

作業ディレクトリはリポジトリの外（`/tmp` 配下など）に作る。生成物はリポジトリに
コミットしない — PNG は重く、履歴に残ると邪魔になる。

## 手順

作業ディレクトリと、スクリプトの場所を変数にしておくと以降が短く書ける。

```bash
WORK=$(mktemp -d)
SKILL=.claude/skills/digest-preview/scripts
```

### 1. フォントを取得する

```bash
$SKILL/fetch_fonts.sh $WORK
```

ページは Google Fonts を参照しているが、実行環境から `fonts.googleapis.com` へ
出られないことがある。その場合フォントが当たらず、**指定した書体ではないもの**で
描画される。取得しておけば撮影時に差し込まれる。
ページが別の書体を読み込むようになったら引数で渡す（例: `$SKILL/fetch_fonts.sh $WORK noto-sans-jp noto-serif-jp`）。

### 2. HTML を描画する

```bash
python3 $SKILL/render.py $WORK/ok.html
python3 $SKILL/render.py $WORK/degraded.html --state degraded
python3 $SKILL/render.py $WORK/fatal.html    --state fatal
```

`--state` は要約の成否。`degraded` は一部のソースだけ失敗（タイトルのみ掲載＋警告バナー）、
`fatal` は全滅（全ソースがタイトルのみ＋打ち切りの警告バナー）。
バナーや劣化表示を変えたときは3つとも撮ること。見落としやすいのは `fatal`。

サンプルデータと `summarize.GROUPS` がずれているとエラーで止まる。
ソースを増やしたら `scripts/sample_data.py` にも足す。

### 3. スクリーンショットを撮る

```bash
python3 $SKILL/shoot.py $WORK/ok.html       $WORK/desktop.png  --width 1280 --height 1500
python3 $SKILL/shoot.py $WORK/ok.html       $WORK/mobile.png   --width 390  --height 1200 --scale 3
python3 $SKILL/shoot.py $WORK/degraded.html $WORK/degraded.png --width 1280 --height 780
```

スマホ幅（390px）は必ず撮る。カードが1列に落ちるところやヘッダーの詰まり具合は、
PC 幅だけ見ていても分からない。

### 4. 撮った画像を必ず自分で見る

撮っただけで報告しないこと。Read ツールで画像を開いて、

- 意図した書体・色になっているか（フォントのフォールバックは見落としやすい）
- カードやバナーが崩れていないか、はみ出していないか
- リンクがリンクに見えるか、コントラストが十分か

を確認する。細部を見るときは Pillow で切り出して拡大すると分かりやすい。

### 5. 変更前後を比べる（任意）

変更前のスクショが残っているなら、1枚にまとめると伝わりやすい。

```bash
python3 $SKILL/compare.py $WORK/before.png $WORK/desktop.png $WORK/compare.png \
  --left-label 変更前 --right-label 変更後 --crop-height 2400
```

変更前の画像は、**CSS を編集する前に** 手順 1〜3 を回して撮っておく必要がある。
デザイン変更に着手する前にまず現状を撮っておくと、後から作り直す手間が省ける。

## デザインの決めごと

このページは[デジタル庁デザインシステム（DADS）](https://design.digital.go.jp/dads/)に
準拠している。色やフォントを足すときは、その場で決めずにトークンから選ぶこと。
値と入手方法は `references/dads-tokens.md` にまとめてある。

## つまずきやすいところ

| 症状 | 原因と対処 |
|---|---|
| 書体が指定と違う | フォント未取得。手順1を実行する。`shoot.py` が警告を出しているはず |
| `Executable doesn't exist` | Playwright と同梱ブラウザの版ずれ。`shoot.py` は既存のものを探すので、それでも出るなら `find_chromium()` の探索パスを足す |
| `ModuleNotFoundError: anthropic` | 準備の `pip install` が済んでいない |
| サンプルデータのズレでエラー | `scripts/sample_data.py` のキーを `summarize.GROUPS` に合わせる |
