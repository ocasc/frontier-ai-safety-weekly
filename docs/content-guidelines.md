# Content guidelines

Rules for writing an issue. They protect the publication's credibility —
break them and the numbers stop being trustworthy.

## Red lines (figures and quotations)

1. **Paper figures and source screenshots are quoted directly with
   attribution. This publication never redraws a paper's figure** — a redrawn
   figure that gets a detail wrong damages credibility more than no figure.
   Translated versions of a figure are allowed only as clearly labelled
   translations ("据原图中译") of the original.
2. **Every card body is structured figure/quotation first, prose after.**
3. **Evidence-class illustrations are original screenshots** (e.g. a tool
   call, a prompt-injection excerpt) with the key line marked by a red
   underline, plus a 「图：…」 caption below.
4. Text-only stories with no usable figure: express the structured content as
   a **hierarchical table** (merged category cells, each row appearing once)
   instead of a quotation block.
5. Quotation block style (if used): light frame, 15 px quote, grey source
   note (`.quote-src`).

Third-party figures and screenshots remain the property of their owners and
are **not** covered by this repository's license (see `NOTICE.md`).

## Factual discipline

- Numbers, dates, and conclusions are restated from the cited source. State
  conditions and limitations together with the finding (sample size,
  simulation vs. real deployment, what was disabled during the test).
- Verify every figure quoted in prose against the source before publishing.
- The footnote states the sourcing policy for the issue.

## Card structure

- Incident-type stories use the three-part form: **经过 / 核心 /
  为什么重要** (what happened / the core issue / why it matters).
- Research/argument stories may use **做了什么 / 核心 / 为什么重要** or a
  mechanism/limits split — keep bold lead-in labels.
- Each card carries `data-category` and `data-importance-rank` (must match
  `importance_order.json`), a `.pnum`, a Chinese title, and a `.title-en`
  line (original title · source · date).

## Translation conventions

- *misalignment* → 错对齐 (consistent throughout).
- Proper nouns, model names, tool names, and exact quantities stay in
  English in translated figures.
