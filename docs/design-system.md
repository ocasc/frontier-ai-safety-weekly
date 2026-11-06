# Design system

The public template is a WeChat 公众号 **long-image** layout rendered in a
480 CSS px viewport at device scale 3, then downsampled to 1080 px output.
At an approximately 358 px content width on a phone, text appears at about
0.75 times its CSS size. `template/issue-template.html` is the source of
truth for this long-image template. Current native text-and-image issues use
a separate production workflow that is not included here.

## Typography

| Element | Size | Notes |
|---|---|---|
| Body (card list items) | 21 px | line-height 1.95 |
| TLDR items (`.map-item`) | 20 px | inside `.tldr-panel` |
| Card title (`.h3`) | 25 px | bold |
| Card number (`.pnum`) | 26 px | bold, no frame, no `#` prefix |
| Figure caption (`.fig-title`) | 21 px | bold, below the figure |
| Meta / link list / footnote | 18 px | grey `#8A9099` |
| Section labels (`.h2` / `.cat-head`) | 21 / 17 px | badges; cat-head stays one line (nowrap) |

Font stack: `"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif`.

## Surfaces

- **Card (`.card`)**: transparent background, 1 px `#4b5563` border, 6 px
  radius, 21 px / 24 px padding.
- **Figure frame**: transparent with a light 1 px border; figures may bleed
  12 px outside the text column (`width: calc(100% + 24px); margin-left: -12px`).
- **Labels**: black badge = section (`TLDR`, `本期链接汇总`); colored badge =
  category (`.cat-head`).
- **Quote block** (`.quote`, kept for future use): light 1 px `#e2e4e8`
  rounded frame, 18 px quote text and grey source note.

## Numbering

Cards are numbered 1–N **in display order**, and the same numbers appear in
the TLDR panel (`.num`) and the link roundup (`.lnum`). The render script
asserts all three sequences. TLDR numbers are bare numerals in the category
color — no chip background, no frame (2026-10-11).

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

| 中文 | Color |
|---|---|
| 错对齐与欺骗 | `#A25433` |
| 控制 | `#3D5A94` |
| 评估与审计 | `#4A6B57` |
| 可解释性 | `#6B5B95` |
| 保证与标准 | `#8A6A3B` |

Categories are ordered by the first appearance of their most important card,
not by the fixed order of this table. A `.map-head` label must match its
`.cat-head` label exactly. Only categories present in an issue are needed.

## Chinese typography

- Full-width punctuation inline in Chinese text; a space between Chinese and
  Latin/digits runs.
