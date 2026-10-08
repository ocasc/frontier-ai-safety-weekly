#!/usr/bin/env python3
"""Render a 900x383 cover card at @2x and @1x.

Usage:
    python3 scripts/render_cover.py template/cover-template.html

Writes <stem>@2x.png (1800x766) and <stem>.png (900x383, LANCZOS downscale)
next to the source HTML.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from render_issue import find_chrome

WIDTH, HEIGHT = 900, 383


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="cover HTML file")
    args = parser.parse_args()
    source = args.source.resolve()
    retina = source.with_name(source.stem + "@2x.png")
    standard = source.with_name(source.stem + ".png")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=find_chrome(), headless=True)
        try:
            page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=2)
            page.goto(source.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.screenshot(path=str(retina))
            page.close()
        finally:
            browser.close()
    with Image.open(retina) as image:
        image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(standard)
    print(retina, Image.open(retina).size)
    print(standard, Image.open(standard).size)


if __name__ == "__main__":
    main()
