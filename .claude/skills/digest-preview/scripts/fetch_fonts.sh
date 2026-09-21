#!/usr/bin/env bash
# スクショ撮影用の Web フォントを npm の @fontsource から取得する。
#
# ページ自体は Google Fonts を参照しているが、実行環境から fonts.googleapis.com へ
# 出られないことがある。その場合フォントが当たらず、ページの書体指定が
# フォールバックで描画されてしまうため、撮影時はここで取得した CSS を差し込む。
#
# 使い方: ./fetch_fonts.sh <作業ディレクトリ> [フォント名...]
set -euo pipefail

out="${1:?作業ディレクトリを指定してください}/fonts"
shift || true
fonts=("$@")
if [ ${#fonts[@]} -eq 0 ]; then
  fonts=(noto-sans-jp)
fi

mkdir -p "$out"
for pkg in "${fonts[@]}"; do
  v=$(curl -sS "https://registry.npmjs.org/@fontsource%2F$pkg" \
      | python3 -c "import sys,json;print(json.load(sys.stdin)['dist-tags']['latest'])")
  curl -sSL -o "$out/$pkg.tgz" "https://registry.npmjs.org/@fontsource/$pkg/-/$pkg-$v.tgz"
  rm -rf "$out/$pkg"
  tar xzf "$out/$pkg.tgz" -C "$out"
  mv "$out/package" "$out/$pkg"
  rm "$out/$pkg.tgz"
  echo "$pkg $v"
done
