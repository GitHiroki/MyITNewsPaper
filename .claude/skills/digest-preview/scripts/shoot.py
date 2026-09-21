"""HTML をヘッドレス Chromium で開いてスクリーンショットを撮る

fetch_fonts.sh で取得したフォント CSS があれば読み込ませる。これをやらないと
Google Fonts へ出られない環境では書体がフォールバックで描画され、
実際のブラウザでの見え方とは違うものを見て判断することになる。

使い方:
    python3 shoot.py <入力.html> <出力.png> [--width 1280] [--height 1500]
                     [--scale 2] [--fonts <fontsディレクトリ>] [--full-page]
"""

import argparse
import asyncio
import glob
import shutil
import sys
from pathlib import Path

from playwright.async_api import async_playwright


def find_chromium() -> str | None:
    """Playwright 同梱の Chromium を探す

    Playwright を更新するとビルド番号が変わり、同梱ブラウザと版がずれて
    「Executable doesn't exist」で落ちる。既にあるものを拾って使う。
    """
    for pattern in (
        "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
        "/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell",
    ):
        found = sorted(glob.glob(pattern))
        if found:
            return found[-1]
    return shutil.which("chromium") or shutil.which("google-chrome")


def font_css_urls(fonts_dir: Path) -> list[str]:
    """@fontsource パッケージの中から、ウェイト別の CSS を集める"""
    if not fonts_dir.is_dir():
        return []
    urls = []
    for pkg in sorted(p for p in fonts_dir.iterdir() if p.is_dir()):
        for sheet in sorted(pkg.glob("[1-9]00.css")):
            urls.append(sheet.as_uri())
    return urls


async def shoot(args) -> None:
    fonts_dir = Path(args.fonts) if args.fonts else Path(args.input).resolve().parent / "fonts"
    css_urls = font_css_urls(fonts_dir)
    if not css_urls:
        print(
            f"警告: {fonts_dir} にフォントがありません。"
            "書体がフォールバックで描画されます（fetch_fonts.sh を先に実行してください）",
            file=sys.stderr,
        )

    launch_kwargs = {}
    executable = find_chromium()
    if executable:
        launch_kwargs["executable_path"] = executable

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        page = await browser.new_page(
            viewport={"width": args.width, "height": args.height},
            device_scale_factor=args.scale,
        )
        await page.goto(Path(args.input).resolve().as_uri())
        if css_urls:
            await page.evaluate(
                """(urls) => Promise.all(urls.map(u => new Promise(resolve => {
                  const link = document.createElement('link');
                  link.rel = 'stylesheet';
                  link.href = u;
                  link.onload = link.onerror = resolve;
                  document.head.appendChild(link);
                })))""",
                css_urls,
            )
        await page.evaluate("document.fonts.ready")
        await page.wait_for_timeout(args.wait)
        await page.screenshot(path=args.output, full_page=args.full_page)
        await browser.close()
    print(args.output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="撮影する HTML")
    parser.add_argument("output", help="出力する PNG")
    parser.add_argument("--width", type=int, default=1280, help="ビューポート幅（既定: 1280）")
    parser.add_argument("--height", type=int, default=1500, help="ビューポート高（既定: 1500）")
    parser.add_argument("--scale", type=int, default=2, help="デバイスピクセル比（既定: 2）")
    parser.add_argument("--fonts", help="フォントディレクトリ（既定: HTML と同じ場所の fonts/）")
    parser.add_argument("--full-page", action="store_true", help="ページ全体を撮る")
    parser.add_argument("--wait", type=int, default=1500, help="描画待ちのミリ秒（既定: 1500）")
    asyncio.run(shoot(parser.parse_args()))


if __name__ == "__main__":
    main()
