# Frontier AI Safety Biweekly — production kit

Template, render pipeline, and editorial rules behind **Frontier AI Safety
Biweekly** (前沿 AI 安全双周刊), a Chinese-language digest for the frontier
AI safety technical community. The publication is scheduled every two weeks.
The repository URL retains its original `weekly` name for existing links.

This public repository contains **tooling, templates and synthetic examples**,
not finished issues, research-source caches or production credentials.
`issues/demo/` is placeholder content for testing. The long-image renderer
here is an earlier production path; current issues may use native WeChat
text-and-image formatting, whose production scripts and content are not
included. This repository is not a complete backup of the live workflow.

Published by [OCASC — Open Community for AI Safety China](https://github.com/ocasc).

## What the pipeline does

`scripts/render_issue.py` takes an issue directory and produces:

1. **Structural QA** — asserts card/TLDR/link numbering runs 1..N, titles and
   categories match the manifest, importance ordering holds, table columns
   match their declared widths, images load, and nothing overflows the
   container.
2. **A 1080 px-wide long image** (3× supersampled, Lanczos-downscaled),
   stitched from short CDP capture tiles —
   Chrome's full-page screenshot silently repeats raster tiles beyond 16,384
   device pixels, corrupting very long captures (see `docs/qa-checklist.md`).
3. **WeChat upload slices** cut at card gaps (each < 15,000 px tall, < 10 MB).
4. **A delivery zip** bundling the HTML, assets, slices, manifest, and check
   dump.

The long-image pipeline is maintained separately from the current native
WeChat production flow. It is not claimed to be behaviorally identical to
the live renderer. The production driver and issue content are not published
here.

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
scripts/edit_serve.py            editable text + autosave-to-disk proofreading server
video/                           narrated explainer pipeline (optional, see video/README.md)
video/prompt_animation.md        model-facing brief for a new animated card
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
3. For the optional cover image, edit and render `template/cover-template.html`
   with `python3 scripts/render_cover.py template/cover-template.html`, then
   copy `template/cover-template@2x.png` to `issues/<id>/img/cover@2x.png`.
   Alternatively, remove the cover `<img>` from the issue HTML.
4. Render:

```bash
python3 scripts/render_issue.py issues/<id>
```

Outputs land next to the source: `<id>.png`, `wechat_upload/part*.png`,
`qa/`, and `<id>.zip`.

Verify the pipeline out of the box with the placeholder issue:

```bash
python3 scripts/render_issue.py issues/demo
```

Run the synthetic regression suite (requires Chrome and the dependencies above):

```bash
python3 -m unittest discover -s tests -v
```

## Live text editing (proofreading)

Serve an issue's HTML with in-browser editable text that writes back to the
same file as you type:

```bash
python3 scripts/edit_serve.py issues/<id>/issue.html
```

Open the printed `http://127.0.0.1:8765/` and edit any text block in place.
Edits autosave to the file (~0.8 s after typing stops; `Ctrl/Cmd+S` forces a
save; closing the tab flushes pending edits; the corner badge shows the save
state). The written-back file is clean: the injected editor script, the badge,
and all `contenteditable`/`spellcheck` attributes are stripped before saving,
and only leaf text nodes are editable, so the markup structure — and the
structural QA assertions — stay intact. The server listens on 127.0.0.1 only,
serves assets from the target file's directory, and writes to that one file.

## Narrated explainer video (optional)

`video/` contains an earlier 1080p narrated motion-graphics workflow. It is
not the current vertical-video production workflow:

1. `narration.py` — MiniMax `t2a_v2` per segment, then `timings.json` + `narration.wav`.
2. `bgm.py` — beat grid plus a music bed trimmed to the exact cut length (crossfade-looped
   when the track is shorter than the video).
3. `render.py` — headless-Chrome frame render of an HTML canvas `renderAt(t)`, ffmpeg encode,
   sidechain-ducked voice/music mix.
4. `audit_video.py` — 3 fps audit for layout-band violations, stalled scenes, blank frames, audio gaps.

No issue content or current video project is committed here. The earlier
workflow and its dependencies are described in `video/README.md`.

## Publishing to WeChat 公众号

The article body cannot contain external links — put the full source list in
「阅读原文」. Create a new 图文 post, insert `wechat_upload/part*.png` strictly
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
