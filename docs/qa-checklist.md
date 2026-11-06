# QA checklist

## Automated (asserted by `scripts/render_issue.py`)

- Card numbers (`.pnum`), TLDR numbers (`.num`), and link numbers (`.lnum`)
  are exactly `1..N`.
- Card titles match `importance_order.json` entries.
- Card `data-category` sequence equals the TLDR `data-category` sequence and
  the manifest; category head labels equal TLDR group head labels.
- Importance ranks match the manifest and are unique positive integers: rank 1
  first, ascending within each contiguous category group, groups ordered by
  their first rank.
- Every table's rendered column widths match its `<colgroup>` percentages.
- All images load; nothing overflows the 480 CSS px viewport.
- The footnote fits inside the captured image.

## Manual (before publishing)

- **Long-image correctness is not proven by DOM checks.** Inspect the actual
  pixels: the top and bottom of every slice boundary, the first card, the
  TLDR panel, and any table.
- Every slice cut must fall in a **gap between output segments** — never
  inside a card. The renderer chooses the midpoint between segment bounds.
- Each WeChat slice: long edge < 15,000 px, file < 10 MB.
- Numbers quoted in prose re-checked against sources (see
  `docs/content-guidelines.md`).

## Known pitfalls

- **Chrome repeats raster tiles beyond 16,384 device pixels** in full-page
  screenshots: the DOM is correct but the image's second half duplicates its
  first. The renderer therefore stitches short CDP `Page.captureScreenshot`
  tiles (≤ 3,000 CSS px each, `captureBeyondViewport`, `clip.scale=1`) at
  device scale 3, then downsamples to the output width. Using `clip.scale>1`
  can re-layout content and shift slice boundaries. Never go back to a
  single `full_page=True` capture for long issues.
- The link roundup's hanging indent lives on `.link-item`, not `.link-list`
  (see `docs/design-system.md`).
- Chrome keeps the screenshot process alive after writing a PNG — scripts
  must kill it, then verify the file with PIL.

## WeChat 公众号 publishing constraints

- The body cannot contain external links — the full source list goes in
  「阅读原文」 (the "read original" link target).
- Single image limits drove the slicing: long edge ≤ 15,000 px, ≤ 10 MB each.
- Publish slices strictly in order (`part1`, `part2`, …).

## Mobile fit

The 480 CSS px canvas exists for the phone: WeChat shows long images at
~358 px content width on a 390 px phone, so on-screen size ≈ CSS font ×
0.75. In the current long-image template, body 21 px → ≈16 px, while
metadata and links 18 px → ≈13.5 px. Check actual issue content on a phone;
small decorative labels do not establish body-text legibility. Figures
embedded at column width always display at ~screen
width regardless of canvas size — screenshot legibility must be fixed by
cropping tighter, not by canvas changes.
