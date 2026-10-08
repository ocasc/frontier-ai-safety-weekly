# Design system

The layout is a WeChat 公众号 long-image: a container rendered at device
scale 2 in a **480 CSS px viewport (960 px output)**. That width is the
readability lever: WeChat displays the image at ~358 px content width on a
390 px phone, so on-screen text size ≈ CSS font × 0.75 — body 16.5 px lands
at ≈12 px, the floor for comfortable reading. Keep content fonts ≥15 px.
`template/issue-template.html` is the
canonical implementation — treat its CSS as the source of truth and this
document as the rationale and rules.

## Typography

| Element | Size | Notes |
|---|---|---|
| Body (card list items) | 16.5 px | line-height 1.95 |
| TLDR items (`.map-item`) | 16 px | inside `.tldr-panel` |
| Card title (`.h3`) | 21 px | bold |
| Card number (`.pnum`) | 22 px | bold, no frame, no `#` prefix |
| Figure caption (`.fig-title`) | 17 px | bold, below the figure |
| Meta / link list / footnote | 15 px | grey `#8A9099` |
| Section labels (`.h2` / `.cat-head`) | 17.5 / 17 px | badges |

Font stack: `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`.

## Surfaces

- **Card (`.card`)**: transparent background, 1 px `#4b5563` border, 6 px
  radius, 21 px / 24 px padding.
- **Figure frame**: transparent with a light 1 px border; figures may bleed
  12 px outside the text column (`width: calc(100% + 24px); margin-left: -12px`).
- **Labels**: black badge = section (`TLDR`, `本期链接汇总`); colored badge =
  category (`.cat-head`).
- **Quote block** (`.quote`, kept for future use): light 1 px `#e2e4e8`
  rounded frame, 15 px quote text, 13 px grey source note.

## Numbering

Cards are numbered 1–N **in display order**, and the same numbers appear in
the TLDR panel (`.num`) and the link roundup (`.lnum`). The render script
asserts all three sequences.

Card order: group cards by category, keep `importance_rank` ascending within
each group, and order groups by their first rank. The
`importance_order.json` manifest records the final numbering and ranks.

## Figures and captions

- Captions always start with 「图：…」 and sit **below** the figure.
- Key emphasis in body text: red text / red frame. On screenshots: red
  underline. Never red highlight bands.

## Link roundup (hanging indent)

Each `.link-item` uses `padding-left: 52px; text-indent: -26px` as its own
block. **Never put `text-indent` on `.link-list`** — block-level indent only
shifts the first line and squeezes item 1's number out of the container.

## Categories and colors

| English (primary) | 中文 | Color | Tint (number chip) |
|---|---|---|---|
| Misalignment | 错对齐案例 | `#A25433` | `#F4EBE6` |
| Oversight & Control | 监督与控制 | `#3D5A94` | `#E9EEF6` |
| Safeguards & Security | 防护与安全 | `#667078` | `#EEF0F2` |
| Safety Cases & System Cards | 安全案例与系统卡 | `#4A6B57` | `#E9F0EC` |

The taxonomy axis is the **research object**, matching the field's standard
split (misalignment reports, scalable oversight / AI control, safeguards,
safety cases), not a media rubric. A `.map-head` label must match its
`.cat-head` label exactly.

## Chinese typography

- Full-width punctuation inline in Chinese text; a space between Chinese and
  Latin/digits runs.
