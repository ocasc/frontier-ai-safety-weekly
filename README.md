# Frontier AI Safety Weekly — production kit

Template, render pipeline, and editorial rules behind **Frontier AI Safety
Weekly** (前沿 AI 安全周刊) — a Chinese-language weekly long-image digest for
the frontier AI safety technical community, laid out for WeChat 公众号
publishing.

This repository contains the **tooling and layout template**. Finished
issues are published as images on WeChat and are not distributed here; the
`issues/demo/` entry is placeholder content that exists to keep the pipeline
verifiable.

Published by [OCASC — Open Community for AI Safety China](https://github.com/ocasc).

## What the pipeline does

`scripts/render_issue.py` takes an issue directory and produces:

1. **Structural QA** — asserts card/TLDR/link numbering runs 1..N, titles and
   categories match the manifest, importance ordering holds, table columns
   match their declared widths, images load, and nothing overflows the
   container.
2. **A 960 px-wide @2x long image**, stitched from short CDP capture tiles —
   Chrome's full-page screenshot silently repeats raster tiles beyond 16,384
   device pixels, corrupting very long captures (see `docs/qa-checklist.md`).
3. **WeChat upload slices** cut at card gaps (each < 15,000 px tall, < 10 MB).
4. **A delivery zip** bundling the HTML, assets, slices, manifest, and check
   dump.

## Repository layout

```
issues/<id>/issue.html           the issue, laid out with the template CSS
issues/<id>/importance_order.json  manifest: title / category / importance_rank
issues/demo/                     placeholder issue (pipeline self-test)
template/issue-template.html     the design system as a working skeleton
template/cover-template.html     900x383 cover card
template/importance_order.example.json
scripts/render_issue.py          render + QA + slice + package
scripts/render_cover.py          cover card at @2x and @1x
scripts/trim_issue.py            trim trailing whitespace of a long image
docs/design-system.md            typography, surfaces, numbering, colors
docs/content-guidelines.md       editorial red lines and card structure
docs/qa-checklist.md             automated + manual QA, known pitfalls
```

## Quickstart

Requirements: Python 3.9+, Google Chrome (or set `CHROME_BIN`), and:

```bash
pip install -r requirements.txt
```

1. Copy `template/issue-template.html` to `issues/<id>/issue.html` and fill
   in the cards (each card needs `data-category` and
   `data-importance-rank`, plus `.title-en`).
2. Copy `template/importance_order.example.json` to
   `issues/<id>/importance_order.json` and list the cards in display order.
3. Render:

```bash
python3 scripts/render_issue.py issues/<id>
```

Outputs land next to the source: `<id>.png`, `wechat_upload/part*.jpg`,
`qa/`, and `<id>.zip`.

Verify the pipeline out of the box with the placeholder issue:

```bash
python3 scripts/render_issue.py issues/demo
```

## Publishing to WeChat 公众号

The article body cannot contain external links — put the full source list in
「阅读原文」. Create a new 图文 post, insert `wechat_upload/part*.jpg` strictly
in order, then title/cover/abstract, preview on a phone, publish.

## License and attribution

- **Code** (`scripts/`): [MIT](LICENSE) — Copyright (c) 2026 Yuanyuan Sun
  and OCASC.
- **Template and docs** (`template/`, `docs/`, issue layouts):
  [CC BY 4.0](LICENSE-CONTENT.md) — attribution: *Frontier AI Safety Weekly
  production kit by Yuanyuan Sun and OCASC*.
- **Third-party figures and screenshots** quoted in issues are not covered
  by these licenses; they remain the property of their owners and are used
  with attribution (see `NOTICE.md`).
