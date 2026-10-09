#!/usr/bin/env python3
"""Render Frontier AI Safety Weekly issues into QA-checked deliverables.

Usage:
    python3 scripts/render_issue.py                 # every issues/*/issue.html
    python3 scripts/render_issue.py issues/demo     # one issue

Per issue directory (issue.html + importance_order.json) this produces:
    <id>.png                  full long image (1080 px wide: 3x supersampled)
    wechat_upload/part*.png   WeChat upload slices cut at card gaps
                              (each < 15,000 px tall and < 10 MB)
    qa/<id>_checks.json       structural check dump
    qa/<id>_qa_*.png          element screenshots for visual QA
    <id>.zip                  delivery package

Why tiles: Chrome's full-page screenshot silently repeats raster tiles
beyond 16,384 device pixels, which corrupts very long captures even though
DOM geometry is correct. We instead capture short CSS-coordinate tiles via
CDP Page.captureScreenshot (captureBeyondViewport, clip.scale=2) and stitch
them at native resolution without rescaling.

Manifest format (issues/<id>/importance_order.json), one entry per card in
display order:
    [{"title": "<.title-en text>", "category": "<data-category>", "importance_rank": 1}, ...]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import math
import os
import sys
import zipfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[1]
CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]
VIEWPORT_WIDTH = 480      # CSS px; keeps on-screen text ≥ ~11px on a 390px phone
DEVICE_SCALE = 3          # 3x supersample; Lanczos down to OUTPUT_WIDTH
OUTPUT_WIDTH = 1080       # WeChat's width ceiling — wider gets force-downscaled + recompressed
SCALE = OUTPUT_WIDTH / VIEWPORT_WIDTH  # final device px per CSS px (2.25)
TILE_HEIGHT = 3000        # CSS px per CDP capture tile
MAX_SLICE_HEIGHT = 14900  # device px; WeChat's cap is 15,000
MAX_SLICE_BYTES = 10_000_000

CHECK_JS = """() => {
 const wlen = s => [...s].reduce((a,ch)=>a+(/[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch)?2:1),0);
  const text = sel => [...document.querySelectorAll(sel)].map(e => e.textContent.trim());
  const rect = e => { const r = e.getBoundingClientRect(); return {x:r.x, y:r.y, w:r.width, h:r.height}; };
  return {
    cards: text('.pnum'),
    tldr: text('.num'),
    links: text('.lnum'),
    titles: text('.title-en'),
    categories: [...document.querySelectorAll('.card')].map(e => e.dataset.category),
    tldrCategories: [...document.querySelectorAll('.map-item')].map(e => e.dataset.category),
    importanceRanks: [...document.querySelectorAll('.card')].map(e => Number(e.dataset.importanceRank)),
    mapHeads: text('.map-head'),
    categoryHeads: text('.cat-head'),
    tableColumns: [...document.querySelectorAll('table')].map(t => [...t.querySelector('tr').cells].map(e => e.getBoundingClientRect().width)),
    declaredColumns: [...document.querySelectorAll('table')].map(t => [...t.querySelectorAll('colgroup col')].map(c => parseFloat(c.style.width) / 100)),
    images: [...document.images].map(e => ({src: e.getAttribute('src'), loaded: e.complete && e.naturalWidth > 0, rect: rect(e)})),
    cardsRect: [...document.querySelectorAll('.card')].map(rect),
    tlLens:[...document.querySelectorAll('.map-item')].map(e=>{const c=e.cloneNode(true); const n=c.querySelector('.num'); if(n)n.remove(); return wlen(c.textContent.trim());}),
    cellLens:[...document.querySelectorAll('td,th')].map(e=>wlen(e.textContent.trim())),
    titleLens:[...document.querySelectorAll('.h3')].map(e=>wlen([...e.childNodes].filter(n=>n.nodeType==3).map(n=>n.textContent).join('').trim())),
    hasMasthead: !!document.querySelector('h1,.issue-head'),
    blocks: [...document.querySelectorAll('.wechat-container > img, .h2, .tldr-panel, .cat-head, .card, .link-list, .footnote')].map(e => ({cls: e.className || 'img', ...rect(e)})),
    scrollWidth: document.documentElement.scrollWidth,
    pageHeight: document.documentElement.scrollHeight,
    footer: rect(document.querySelector('.footnote')),
    nodes: [...document.querySelectorAll('.card,.link-item,table')].map(rect),
    tldrPanel: document.querySelector('.tldr-panel') ? true : false
  };
}"""


def find_chrome() -> str:
    override = os.environ.get("CHROME_BIN")
    if override:
        return override
    for path in CHROME_CANDIDATES:
        if Path(path).exists():
            return path
    sys.exit("Chrome not found; set CHROME_BIN to a Chrome/Chromium binary.")


def load_manifest(issue_dir: Path) -> list:
    manifest = json.loads((issue_dir / "importance_order.json").read_text())
    assert isinstance(manifest, list) and manifest, "importance_order.json must be a non-empty list"
    for row in manifest:
        assert {"title", "category", "importance_rank"} <= set(row), row
    return manifest


def run_checks(page, manifest: list, label: str) -> dict:
    checks = page.evaluate(CHECK_JS)
    n = len(manifest)
    sequence = [str(i) for i in range(1, n + 1)]
    for field in ["cards", "tldr", "links"]:
        assert checks[field] == sequence, (label, field, checks[field])
    assert checks["titles"] == [r["title"].strip() for r in manifest], (label, "titles")
    assert not checks["hasMasthead"], (label, "no masthead/headline block: WeChat has its own title")
    assert max(checks["tlLens"], default=0) <= 100, (label, "TLDR item over 50 CJK-width", checks["tlLens"])
    assert max(checks["cellLens"], default=0) <= 90, (label, "table cell over 45 CJK-width", checks["cellLens"])
    assert max(checks["titleLens"], default=0) <= 84, (label, "title over 42 CJK-width", checks["titleLens"])
    assert checks["categories"] == [r["category"] for r in manifest], (label, "card categories")
    assert checks["tldrCategories"] == [r["category"] for r in manifest], (label, "TLDR categories")
    assert len(checks["categoryHeads"]) == len(set(checks["categories"])), (label, "category heads")
    assert checks["categoryHeads"] == checks["mapHeads"], (label, "heads mismatch")
    ranks = [r["importance_rank"] for r in manifest]
    assert checks["importanceRanks"] == ranks, (label, "importance ranks")
    assert checks["importanceRanks"][0] == 1, (label, "first card must hold rank 1")
    category_order = list(dict.fromkeys(checks["categories"]))
    groups = [[r for r, c in zip(ranks, checks["categories"]) if c == cat] for cat in category_order]
    for group in groups:
        assert group == sorted(group), (label, "ranks ascending within category", group)
    firsts = [g[0] for g in groups]
    assert firsts == sorted(firsts), (label, "categories ordered by first rank", firsts)
    for widths, ratios in zip(checks["tableColumns"], checks["declaredColumns"]):
        total = sum(widths)
        assert len(widths) == len(ratios) and abs(sum(ratios) - 1) < 0.001, (label, widths, ratios)
        assert all(abs(w / total - r) < 0.005 for w, r in zip(widths, ratios)), (label, widths)
    assert all(image["loaded"] for image in checks["images"]), (label, "images failed to load")
    assert checks["scrollWidth"] == VIEWPORT_WIDTH, (label, checks["scrollWidth"])
    for rect in checks["nodes"]:
        assert rect["x"] >= -1 and rect["x"] + rect["w"] <= VIEWPORT_WIDTH + 1, (label, rect)
    assert checks["tldrPanel"], (label, "missing .tldr-panel")
    return checks


def capture_long(page) -> Image.Image:
    tiles = []
    cdp = page.context.new_cdp_session(page)
    # Emulation override + capture in ONE CDP session (a second session drops
    # the scale). clip.scale must stay 1: clip.scale>1 re-lays-out at the clip
    # zoom and drifts the raster ~3.5% from DOM rects (cuts cards at seams).
    cdp.send("Emulation.setDeviceMetricsOverride",
             {"width": VIEWPORT_WIDTH, "height": 900,
              "deviceScaleFactor": DEVICE_SCALE, "mobile": False})
    for y in range(0, page.evaluate("document.documentElement.scrollHeight"), TILE_HEIGHT):
        capture = cdp.send("Page.captureScreenshot", {
            "format": "png",
            "captureBeyondViewport": True,
            "clip": {"x": 0, "y": y, "width": VIEWPORT_WIDTH,
                     "height": min(TILE_HEIGHT, page.evaluate("document.documentElement.scrollHeight") - y),
                     "scale": 1},
        })
        tiles.append(Image.open(io.BytesIO(base64.b64decode(capture["data"]))).convert("RGB"))
    cdp.detach()
    stitched = Image.new("RGB", (VIEWPORT_WIDTH * DEVICE_SCALE, sum(t.height for t in tiles)), "white")
    offset = 0
    for tile in tiles:
        stitched.paste(tile, (0, offset))
        offset += tile.height
    # 3x supersample, Lanczos down to the 1080px WeChat ceiling (crisper than native 2.25x).
    return stitched.resize((OUTPUT_WIDTH, round(stitched.height * OUTPUT_WIDTH / stitched.width)),
                           Image.Resampling.LANCZOS)


def split_for_wechat(image: Image.Image, blocks: list, out_dir: Path, label: str) -> list:
    """One picture per article: [cover] [TLDR] [card x N] [links+footnote].
    A cat-head banner rides with the card it introduces; boundaries sit at gap
    midpoints (white by construction)."""
    segs = []
    for blk in blocks:
        cls = blk["cls"]
        if cls in ("img", "h2", "cat-head"):
            segs.append([blk])
        elif cls.split()[0] == "card":  # tolerates legacy 'card deep'
            if segs and len(segs[-1]) == 1 and segs[-1][0]["cls"] == "cat-head":
                segs[-1].append(blk)
            else:
                segs.append([blk])
        else:  # tldr-panel / link-list / footnote join the heading above
            assert segs, (label, cls)
            segs[-1].append(blk)
    bounds = [0]
    for i in range(len(segs) - 1):
        bot = max(b["y"] + b["h"] for b in segs[i])
        top = min(b["y"] for b in segs[i + 1])
        bounds.append((math.floor(bot * SCALE) + math.ceil(top * SCALE)) // 2)
    bounds.append(image.height)
    part, files = 1, []
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(len(segs)):
        start, end = bounds[i], bounds[i + 1]
        assert 0 < end - start < 15000, (label, part, end - start)
        upload = out_dir / f"part{part}.png"
        image.crop((0, start, image.width, end)).convert("RGB").save(upload, "PNG")
        assert end - start < 15000 and upload.stat().st_size < MAX_SLICE_BYTES, (label, upload)
        print(f"  slice {upload.relative_to(REPO)} {image.width}x{end - start} {upload.stat().st_size // 1024} KB")
        files.append(upload)
        part += 1
        start = end
    return files


def render_issue(browser, issue_dir: Path) -> Path:
    issue_dir = issue_dir.resolve()
    label = issue_dir.name
    source = issue_dir / "issue.html"
    manifest = load_manifest(issue_dir)
    page = browser.new_page(viewport={"width": VIEWPORT_WIDTH, "height": 900}, device_scale_factor=DEVICE_SCALE)
    try:
        page.goto(source.as_uri(), wait_until="load")
        page.evaluate("document.fonts.ready")
        checks = run_checks(page, manifest, label)

        output = issue_dir / f"{label}.png"
        capture_long(page).save(output)

        qa_dir = issue_dir / "qa"
        qa_dir.mkdir(exist_ok=True)
        page.locator(".tldr-panel").screenshot(path=str(qa_dir / f"{label}_qa_tldr.png"))
        page.locator(".card").first.screenshot(path=str(qa_dir / f"{label}_qa_first.png"))
        (qa_dir / f"{label}_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))

        with Image.open(output) as image:
            assert checks["footer"]["y"] * SCALE + checks["footer"]["h"] * SCALE <= image.height + 2, \
                (label, "content taller than capture")
            slices = split_for_wechat(image, checks["blocks"], issue_dir / "wechat_upload", label)

        package = issue_dir / f"{label}.zip"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(source, "issue.html")
            for image_info in checks["images"]:
                z.write(issue_dir / image_info["src"], image_info["src"])
            for upload in slices:
                z.write(upload, "wechat_upload/" + upload.name)
            z.write(issue_dir / "importance_order.json", "importance_order.json")
            z.write(qa_dir / f"{label}_checks.json", "render_checks.json")
        with zipfile.ZipFile(package) as z:
            assert z.testzip() is None
        print(f"  {label}: {len(manifest)} cards PASS (numbering, categories, ranks, tables, images, overflow)")
        return package
    finally:
        page.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("issues", nargs="*", type=Path,
                        help="issue directories (default: every issues/*/ with an issue.html)")
    args = parser.parse_args()
    dirs = [d for d in args.issues] if args.issues else sorted(
        d for d in (REPO / "issues").glob("*/") if (d / "issue.html").exists())
    assert dirs, "no issue directories found"
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=find_chrome(), headless=True)
        try:
            for issue_dir in dirs:
                print(f"rendering {issue_dir} ...")
                package = render_issue(browser, issue_dir)
                print(f"  package: {package.relative_to(REPO)}")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
