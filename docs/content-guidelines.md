# Content guidelines

Rules for writing an issue. They protect the publication's credibility —
break them and the numbers stop being trustworthy.

## Red lines (figures and quotations)

1. **Paper figures and source screenshots are quoted directly with
   attribution. This publication never redraws a paper's figure** — a redrawn
   figure that gets a detail wrong damages credibility more than no figure.
   Translated versions of a figure are allowed only as clearly labelled
   translations ("据原图中译") of the original.
2. **When using a figure or quotation, put it before the related prose.**
3. **Evidence-class illustrations are original screenshots** (e.g. a tool
   call, a prompt-injection excerpt) with the key line marked by a red
   underline, plus a 「图：…」 caption below.
4. Prefer a meaningful figure when available. Use a table for parallel items
   with a genuinely comparable structure; otherwise use clear prose. Avoid
   repeating in prose what the figure or table already shows.
5. Quotation block style (if used): light frame, 18 px quote, grey source
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

- Use **做了什么 / 结果 / 为什么重要** as the default structure. If a
  card compares independent pieces of work, group by the actual subject
  rather than forcing the same structure onto both.
- Maintain source, numbers, conditions and uncertainty when shortening text.
- Each card carries `data-category` and `data-importance-rank` (must match
  `importance_order.json`), a `.pnum`, a Chinese title, and a `.title-en`
  line (original title · source · date).

## Translation conventions

- *misalignment* → 错对齐 (consistent throughout).
- Proper nouns, model names, tool names, and exact quantities stay in
  English in translated figures.
