# デジタル庁デザインシステム（DADS）のトークン

digest ページの配色・書体・角丸は [DADS](https://design.digital.go.jp/dads/) に準拠している。
実際の値は `summarize.py` の `STYLE` 冒頭に CSS 変数として定義してあるので、
まずはそこを見る。ここは「なぜその値なのか」と「増やしたいときにどこから取るか」の控え。

## 値の入手方法

公式サイト `design.digital.go.jp` は実行環境のプロキシで遮断されていることがある。
その場合でも npm レジストリには出られるので、公式パッケージから取れる。

```bash
curl -sSL -o tokens.tgz \
  https://registry.npmjs.org/@digital-go-jp/design-tokens/-/design-tokens-2.0.1.tgz
tar xzf tokens.tgz
cat package/dist/tokens.css          # 色 + フォント + 行間 + 角丸
cat package/dist/tokens-simple.css   # 色とフォントのみ
```

最新版を確認するなら `curl -sS https://registry.npmjs.org/@digital-go-jp/design-tokens`。

## 使っている値（v2.0.1）

| 用途 | トークン | 値 |
|---|---|---|
| キーカラー（リンク・見出しの罫） | Blue-900 | `#0017c1` |
| キーカラー濃いめ（hover・カード見出し文字） | Blue-1000 | `#00118f` |
| 訪問済みリンク | Blue-1200 | `#000060` |
| カード見出しの地 | Blue-50 | `#e8f1fe` |
| カード見出しの罫 | Blue-100 | `#d9e6ff` |
| 日付バッジの枠 | Blue-200 | `#c5d7fb` |
| 本文 | Solid Gray 900 | `#1a1a1a` |
| バナー本文 | Solid Gray 800 | `#333333` |
| 補足・要約文 | Solid Gray 700 | `#4d4d4d` |
| 件数などの弱いテキスト | Solid Gray 536 | `#767676` |
| カードの枠 | Solid Gray 200 | `#cccccc` |
| リスト項目の区切り | Solid Gray 100 | `#e6e6e6` |
| ページ背景 | Solid Gray 50 | `#f2f2f2` |
| 警告バナー | Yellow-700 | `#b78f00` |
| 成功表示 | Green-600 | `#259d63` |
| フォーカスリング | Yellow-400 | `#ffc700` |

- 角丸: カードなどの面は 8px、小さい要素は 4px、バッジは全丸
- 書体: Noto Sans JP（400 / 500 / 700）
- 行間: 本文 1.7、見出し 1.5

## 押さえておきたい考え方

- **Solid Gray 536 (`#767676`) が白背景で 4.5:1 を満たす下限**。
  補足テキストをこれより薄くしない。
- **リンクは色だけで区別しない**。キーカラー＋下線にする。色覚特性によっては
  色の差が伝わらないため。
- **フォーカスインジケーターは黒アウトライン＋黄色リング**。
  キーボード操作でどこにいるか分かるようにする。背景色に関係なく見えるのが黄色＋黒の理由。
- 面の区切りは影ではなく枠線と地色で作る。DADS は影を多用しない。

## 補色・状態色を足したくなったら

セマンティックカラー（success / error / warning）は上記パッケージの
`--color-semantic-*` に定義がある。自分で hex を決めずにそこから取る。
