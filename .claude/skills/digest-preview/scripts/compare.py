"""2枚のスクリーンショットを、ラベル付きで横並びにした比較画像を作る

変更前後を1枚にまとめておくと、レビューやチャットに貼ったときに伝わりやすい。

使い方:
    python3 compare.py <左.png> <右.png> <出力.png>
                       [--left-label 変更前] [--right-label 変更後]
                       [--crop-height 2400] [--max-width 2800]
"""

import argparse

from PIL import Image, ImageDraw, ImageFont

# 日本語ラベル用。無ければ既定フォントにフォールバックする
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
]
LABEL_HEIGHT = 96
GAP = 32
PAD = 32


def load_font(size: int):
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left")
    parser.add_argument("right")
    parser.add_argument("output")
    parser.add_argument("--left-label", default="変更前")
    parser.add_argument("--right-label", default="変更後")
    parser.add_argument("--crop-height", type=int, help="上から指定ピクセルだけ切り出す")
    parser.add_argument("--max-width", type=int, default=2800, help="出力の最大幅（既定: 2800）")
    args = parser.parse_args()

    left = Image.open(args.left).convert("RGB")
    right = Image.open(args.right).convert("RGB")
    if args.crop_height:
        left = left.crop((0, 0, left.width, min(args.crop_height, left.height)))
        right = right.crop((0, 0, right.width, min(args.crop_height, right.height)))

    # 高さを揃えないと横並びにしたときに比較しづらい
    height = min(left.height, right.height)
    left = left.crop((0, 0, left.width, height))
    right = right.crop((0, 0, right.width, height))

    width = PAD * 2 + left.width + GAP + right.width
    canvas = Image.new("RGB", (width, LABEL_HEIGHT + height + PAD), "#ffffff")
    canvas.paste(left, (PAD, LABEL_HEIGHT))
    canvas.paste(right, (PAD + left.width + GAP, LABEL_HEIGHT))

    draw = ImageDraw.Draw(canvas)
    font = load_font(44)
    draw.text((PAD, 26), args.left_label, font=font, fill="#767676")
    draw.text((PAD + left.width + GAP, 26), args.right_label, font=font, fill="#0017c1")
    for x, image in ((PAD, left), (PAD + left.width + GAP, right)):
        draw.rectangle(
            [x, LABEL_HEIGHT, x + image.width - 1, LABEL_HEIGHT + height - 1],
            outline="#cccccc",
        )

    if canvas.width > args.max_width:
        ratio = args.max_width / canvas.width
        canvas = canvas.resize((args.max_width, int(canvas.height * ratio)), Image.LANCZOS)

    canvas.save(args.output)
    print(f"{args.output} {canvas.size}")


if __name__ == "__main__":
    main()
