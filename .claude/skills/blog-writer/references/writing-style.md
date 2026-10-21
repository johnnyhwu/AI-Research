# Voice guide: 台灣繁體中文，讀起來像工程師寫的，不像 AI 生成的

The concrete "how" behind `SKILL.md`'s hard rules 2 and 3. Read it before
drafting; style is easier to get right from the first sentence than to
retrofit.

**Write directly in Chinese. Don't draft in English and translate.**
Translating a finished English draft drags English sentence rhythm along even
when every word is right. Think through the arc, then write each section in
Chinese from the start.

## Terminology: Taiwan usage, not PRC usage

Translate the paper's English terms with the word a Taiwanese engineer would
reach for (avoid → use):

| Avoid | Use |
|---|---|
| 软件 / 硬件 | 軟體 / 硬體 |
| 程序 (code) | 程式 |
| 数据 | 資料 |
| 算法 | 演算法 |
| 用户 | 使用者 |
| 服务器 | 伺服器 |
| 网络 | 網路 |
| 内存 | 記憶體 |
| 缓存 | 快取 |
| 队列 | 佇列 |
| 带宽 | 頻寬 |
| 质量 | 品質 |
| 信息 | 資訊 |
| 视频 | 影片 |
| 文件 (a file) | 檔案 |
| 默认 | 預設 |
| 优化 | 優化 (check no simplified variant slipped in) |

Also avoid mainland-flavored wording such as 走查 (use 逐步試算 / 逐步演算).
If a term feels like it came from a Simplified-Chinese tech doc, look for the
Taiwan-community equivalent (iThome, Taiwanese Medium posts). Keep one spelling
per word across the article (暴露, 占).

Use full-width punctuation in Chinese prose (，。；：？！「」『』), including
headings and table cells. Semicolons and colons are the ones that slip through
half-width. Exceptions: a digit-to-digit thousands separator (`4,000`), and
punctuation inside an English quote, inline code or URL.

## Sentence and paragraph rhythm

Avoid these recognizable AI tics:

- **Uniform medium-length sentences.** Mix short sentences that land a point
  with longer ones that walk through a mechanism.
- **The em-dash (——) as universal glue.** Occasional is fine; use parentheses,
  a colon, or a new sentence otherwise.
- **Formulaic enumeration** ("首先...其次...再者...最後...") in running prose.
  Fine for an actual list.
- **Filler transitions**: 值得注意的是、毫無疑問、眾所周知、不可否認、總而言之. If the
  sentence works without it, delete it.
- **Restating the same point twice in a row** ("這意味著 X。換句話說，X。").
- **Over-bolding.** Bold a term's first introduction or a genuinely
  load-bearing point, not every paragraph.
- **Tour-guide narration** ("讓我們一起來看看", "接下來我們將深入探討"). State
  things; don't announce that you're about to.

## Formal definitions and symbols: LaTeX

A genuine formal definition (named variables, `=`, set/operator notation like
`A(T) = {r} ∪ {...}`) is LaTeX, `$...$` inline or `$$...$$` as a block, not a
plain-text code fence. It is standard notation, not platform syntax, and Step 3
only has to swap delimiters for the site's math renderer.

The rule covers **every symbol, wherever it appears**; the usual miss is the
scattered inline reference. "策略 π_{t+1}。" ships raw LaTeX source into the
prose; `V^0`, `π^m`, `β1`, `M-1`, `10^15` read the same way. Table cells and
headers count (`分數 s_v`, `k*=3`, a `分數 V` column header). **Convert
completely**: a raw symbol next to a converted one looks worse than leaving the
whole sentence alone, so when a sentence gets any math, sweep all of it, single
capitals (`W`, `M`, `C`, `N`) included. Don't use a bare `$` for currency
(`$1.20` reads as a math delimiter); write 美元.

**Keep `$$...$$` display blocks out of list items.** A formula tucked under a
bullet is the one shape Step 3 can't convert mechanically. Finish the list,
then put each display formula on its own line at the top level, blank lines
around it, with a lead-in sentence.

Reserve code fences for what is procedural: a round-by-round trace with real
numbers, or literal code. A fence of `r = 根節點, ...` is a formula in a code
block costume, and a reader's eye skips it. When a walkthrough mixes both,
split them: LaTeX for the definition, a fence (or numbered list) for the trace.
Put prose explanations of a code block's comments in the sentence above it
rather than as `#` lines at column 0.

## Structural readability

Correct, well-voiced prose can still be hard to follow. Mechanical checks:

- **One idea per paragraph, 2-3 sentences, point first.** A paragraph past
  ~150 字 is usually doing too much; split it.
- **Don't let the opening stall.** Get to the first concrete claim quickly.
- **Re-anchor terms that resurface much later** with a short parenthetical
  ("...（也就是前面提到的 XXX）...").
- **Explain a term before using it**, even a common one (pp, 信賴區間, 快取) if
  the reader hasn't met it yet.
- **Every abstract mechanism gets one concrete example**: a number, a
  before/after, a situation an engineer recognizes.
- **A/B comparisons go in a table or parallel bullets**, not running prose.
- **Concise `## 前言` and `## 結論`**, each its own heading. 前言 states the
  point and scope in a couple of short paragraphs; 結論 is a quick recap, not a
  re-argument. If either runs as long as a body section, trim it.
- **One `#` in the whole file** (the title). All other top-level sections,
  including any tangential theme, are `##`; that theme's sub-topics are `###`
  under one `##`, never sibling `##`s (which flattens them into an unrelated
  wall; this shipped wrong once).
- **One home per explanation.** If a recap section and a deep-dive section
  cover the same concept, explain it fully in one and point to it from the
  other in a line. Cross-references name a heading that exists, and visuals are
  referred to by the article's own 表 N / 圖 N (see `figure-map-schema.md`).

## Cross-document structural repetition

Some failures only show zoomed out: the same structural move repeated until it
reads as a template. Skim the finished draft for:

- every blockquote/aside opening or closing the same way, 3+ times;
- every section ending on the same kind of line (e.g. always "...脫離這篇論文也
  成立"; once is a callback, four times is a template);
- every H2/H3 opening with the same sentence shape (always a rhetorical
  question, always "先講結論：...");
- a closing "lessons" list that restates earlier points in identical words
  instead of compressing them.

One or two repeats is style; three or more is the pattern doing the writing.
Vary the move, not just the vocabulary.

## Keeping a long, complete article navigable

Per hard rule 5 the article keeps nearly everything in the notes, so length is
expected. Make it navigable, not short:

- **Give tangential-but-valuable material its own headed section** rather than a
  footnote-sized aside, so a reader who wants only the paper can skip it by its
  title.
- **Open a long section with a short lead-in** ("30秒版本" style) saying what
  the reader is about to get.
- **Use blockquotes for asides, caveats and "the notes flagged this as
  uncertain" callouts.**
- **Keep worked examples intact.** A step-by-step walkthrough with real numbers
  teaches better than a summary and is the first thing tempting to cut; compress
  the prose around it instead.
- **Use tables for anything the notes already structured as one,** and promote
  dense contrast paragraphs to tables.
- **Use `---` breaks and sub-headings** between major movements.
- **Hang everything on a narrative spine** (see `writer-reviewer-spec.md`) rather
  than appending in note order.

## The natural voice

- Direct, a little conversational, still precise: a senior engineer explaining
  something to a colleague. A phrase like 說白了、白話一點來說、老實說、這裡的眉角是、
  踩雷 now and then is good; one or two per article is plenty.
- State a claim, then ground it at once in a number, mechanism or example.
- Framing a section around a problem an engineer has hit is good, once or twice
  per article, not as a template at every section top.
- Plain about limitations: "這裡有個很現實的限制" beats "值得注意的是，這可能存在某些
  潛在的限制".

## Self-check before finishing a draft

- Read a paragraph out loud (mentally): a person talking to a colleague, or a
  characterless summary?
- Scan for the tics above (em-dash density, enumeration, filler, over-bolding);
  a paragraph with more than one gets rewritten.
- Check the terminology table against the most frequent nouns, since a wrong
  term compounds.
