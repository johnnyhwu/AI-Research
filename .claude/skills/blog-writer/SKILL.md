---
name: blog-writer
description: Use this skill whenever you need to write or revise article.md for a topic directory in this repo's blog-writing pipeline (Step 2 -- Writer + Reviewer), triggered by phrases like "開始產生 blog", "generate the blog/post for &lt;dir&gt;", "write the article for &lt;dir&gt;", or "幫 &lt;dir&gt; 寫文章". Turns a topic directory's discussion-notes/chatlog file (never the source PDF, never any image) plus its image-manifest.json's text fields (caption/page/type/nearby_text only) into a polished, platform-neutral article.md written in Traditional Chinese (Taiwan usage), through an in-session Writer &lt;-&gt; Reviewer loop where the Reviewer runs as an independent subagent that reads article.md from disk rather than having it pasted in. This skill is fully self-contained: no external spec document is needed or will be supplied to run it -- this file plus references/ is the complete, current spec.
---

# Blog Writer (Step 2: Writer + Reviewer)

The complete spec for Step 2 of this repo's pipeline (see the repo
`CLAUDE.md`). This file plus `references/` is all there is; nothing else will
be supplied.

## Hard rules

1. **Never read the source PDF or open any image.** Your only sources of fact
   are the topic directory's notes/chatlog file and the `caption` / `page` /
   `type` / `nearby_text` text fields of `image-manifest.json`. Fact-checking
   and crop-checking were Step 1's job. If you want to peek "just to confirm",
   the notes were underspecified; write around the gap (flag it, don't fake
   it) instead.
2. **Prose is Traditional Chinese, Taiwan usage (台灣繁體中文)**: headings,
   alt text and visible captions included. Not English, not Simplified, not a
   mix. The one exception is each `figure-map` entry's
   `references_manifest_caption`, which stays verbatim in the manifest's
   language.
3. **Write like a Taiwanese AI/software engineer wrote it by hand**, not like
   generic AI output. Concrete dos/don'ts: `references/writing-style.md`.
4. **The reader has never read the paper.** Readability and correctness
   outrank brevity. When unsure whether something needs explaining, explain it.
5. **Preserve the notes' depth; solve readability with structure, not
   deletion.** Carry forward everything substantive: explanations, worked
   examples, caveats, asides, and especially anything the notes flag as
   independently valuable ("獨立於論文本身", "建議優先閱讀", "真正的重點"). If
   the notes read as two parts (the paper itself, and standalone lessons), the
   article visibly carries both. Manage length with headings, sub-sections,
   tables and callouts. The only cuts allowed are true redundancy and the
   notes' own meta-commentary about note-taking.

## Inputs

In `<dir>/`:
- the notes/chatlog file (`.txt`, `.md`, `.json`; detect by what's there). Your
  primary and only source of facts.
- `assets/image-manifest.json` (check the repo `CLAUDE.md` for per-topic
  exceptions before assuming the path). Read only `id` / `caption` / `page` /
  `type` / `nearby_text`.

### If there's no manifest

If the directory has a source PDF, **stop and run Step 1
(`pdf-figure-table-parser`) first, then write.** Writing first means rewriting
every figure mention, rebuilding the `figure-map`, and re-running the whole
review loop.

The fallback is only for topics where a manifest isn't achievable (no PDF, or
Step 1 genuinely extracted nothing); say which applies when you report. Write
the article with figures referenced descriptively in prose (never an invented
id), an **empty** `figure-map` (`` ```figure-map\n[]\n``` ``), and this exact
line first in the file:
`<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match manually -->`

## Workflow

1. **Read the notes in full.** Narrative, emphasis, and which figures/tables
   the user wants are all here. Explicit callouts ("插入 Figure 1 這裡") are the
   shortlist; a visual earns a place by supporting a paragraph, not by existing.
2. **Read the manifest's text fields**, matching the notes' callouts to ids by
   caption content, never by guessing a number.
3. **Write the first draft** to the bar in `references/writer-reviewer-spec.md`
   (narrative arc over transcript replay, first-principles explanations,
   honest limitations, own-words paraphrase, a figure only where it helps).
   Specifics that are easy to miss:
   - an explicit concise `## 前言` right after the title and a `## 結論`
     (quick recap, not a re-argument) as the last section before `figure-map`;
   - exactly one `#` (the title); every other top-level section, including any
     independent theme from rule 5, is `##`, with sub-topics nested as `###`;
   - formal definitions and every symbol are LaTeX (`$...$`/`$$...$$`), see
     `writing-style.md`;
   - figures as `![alt](img-00N)` plus an italic caption, numbered in article
     order, and a single trailing `figure-map` block covering exactly the
     referenced ids (`references/figure-map-schema.md`);
   - no Hugo front matter or shortcodes (Step 3's job).
   Before review, do a **coverage pass**: walk the notes' section list and
   confirm each major point has a home. "It didn't fit the narrative" is not a
   reason to drop one.
4. **Send it to the Reviewer, an independent subagent, by path.** Spawn a
   fresh subagent (no memory of this conversation, so the prompt must be
   self-contained) with the exact path to `article.md` and the prompt below.
   Never paste the article into the prompt.

   > Read the file at this exact path and review it: `<path-to-article.md>`
   >
   > Do not read any other file (no PDF, no images, no manifest, no notes
   > file). Adopt the persona of an ordinary web reader with no prior
   > knowledge of the paper, who cannot see the source PDF or any notes: only
   > this file. Your job is strictly READABILITY, not factual correctness (you
   > can't verify facts, so don't try). This is a long-form deep-dive, so
   > don't flag length or thoroughness by itself; flag only a specific passage
   > that rambles, restates a point already made, or loses the thread. Assess:
   > is it easy to follow for a newcomer, is the pacing right, does
   > layout/figure placement read naturally, and are there typos, awkward
   > phrasing or self-contradictions? Also flag: a paragraph that buries its
   > point after a long wind-up or does more than one thing; a jargon
   > term/acronym that resurfaces much later with no reminder, or is used
   > before it is explained; an abstract claim about what a method "does" with
   > no concrete example; an A/B comparison left as prose instead of a
   > table/parallel bullets; a missing or unheaded 前言/結論, an intro that
   > stalls, or a conclusion that re-argues the whole piece. The article
   > should be Traditional Chinese (Taiwan usage), so flag English, Simplified
   > Chinese, or AI-sounding translationese, and half-width , ; : ? ! in
   > Chinese prose (headings and table cells included; digit-to-digit
   > thousands separators and code/URLs are fine). Also flag: (a) more than
   > one top-level `#`, or a tangential theme whose sub-topics sit at `##`
   > instead of `###` under one `##`; (b) the same blockquote opener/closer,
   > section wrap-up line or heading shape repeated 3+ times across the whole
   > article (read end to end for this); (c) a formal definition in a
   > plain-text code fence instead of LaTeX, or raw notation (`s_v`, `π_{t+1}`,
   > `分數 V`) in prose or a table cell outside `$...$`; (d) cross-reference
   > problems: a 表 N/圖 N in the prose that doesn't match the numbering of the
   > captions, two numbering schemes in play, or a pointer to a section by a
   > name that no heading has; (e) the same content explained in full in more
   > than one place. Do not comment on the trailing `figure-map` block.
   >
   > If there's nothing worth fixing, your entire output must be exactly one
   > line: `REVIEW_APPROVED_NO_CHANGES`. Otherwise give concrete, actionable
   > feedback (quote the sentence, say what's wrong, say what you'd change) and
   > do not emit that token. Don't manufacture nitpicks that wouldn't bother a
   > real reader; approve instead.

   If no subagent tool is reachable (check first), do the review yourself:
   re-read `article.md` fresh from disk, apply the same checklist, give the
   same verdict, and state the deviation in your final report instead of
   presenting a single Writer pass as if the loop ran.

5. **Loop, at most 3 Writer→Reviewer cycles.** Apply the feedback in place,
   then resume the *same* subagent (`SendMessage` to its id; it already knows
   what it flagged) with the same path. Stop early on
   `REVIEW_APPROVED_NO_CHANGES`; after 3 cycles keep the latest version. If a
   cycle's remaining items are a handful of small, mechanical fixes, apply them
   and stop rather than spending another cycle; say so in the report. Edit
   style: targeted `Edit` calls for localized fixes, a short script
   (`sed`/Python) for mechanical sweeps (punctuation, a term renamed
   everywhere), `Write` only when the structure itself changes.
6. **Verify.**
   ```bash
   python .claude/skills/blog-writer/scripts/verify_article.py <dir>/article.md \
     --manifest <dir>/assets/image-manifest.json
   ```
   It checks the `figure-map` is valid JSON with ids exactly matching the body
   and the manifest (captions verbatim), no Hugo shortcodes, one `#`,
   前言/結論 present, sequential 表/圖 caption numbering, no paper-numbered
   `Table N`/`Figure N` left in prose, CJK density, full-width punctuation,
   and raw notation. Omit `--manifest` for the `NO-MANIFEST` case.

## Definition of done

- `article.md` reads well to a naive reader, reflects the notes honestly
  (caveats included), and keeps their substance (coverage pass found nothing
  dropped except true redundancy).
- Every body image `src` is a manifest `id` (or the file carries the
  `NO-MANIFEST` note), the `figure-map` is valid and complete, and there is no
  Hugo syntax.
- `verify_article.py` passes.
- The topic is moved to `done/unpublished/` with its manifest paths rewritten
  and `verify_manifest.py` re-run (repo `CLAUDE.md`, "Moving a topic between
  buckets"), and the task is finished per "Finishing a task" there. Leaving
  the directory in `in-progress/` is an unfinished task.

## Files

```
blog-writer/
├── SKILL.md
├── references/
│   ├── writer-reviewer-spec.md   writing-quality bar + review-loop details
│   ├── figure-map-schema.md      image reference convention + figure-map schema
│   └── writing-style.md          Traditional Chinese (Taiwan) voice guide
└── scripts/verify_article.py
```
