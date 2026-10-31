---
name: blog-writer
description: Use this skill whenever you need to write or revise article.md for a topic directory in this repo's blog-writing pipeline (Step 2 -- Writer + Reviewers), triggered by phrases like "開始產生 blog", "generate the blog/post for &lt;dir&gt;", "write the article for &lt;dir&gt;", or "幫 &lt;dir&gt; 寫文章". Turns a topic directory's discussion-notes/chatlog file (never the source PDF, never any image) plus its image-manifest.json's text fields (caption/page/type/nearby_text only) into a polished, platform-neutral article.md written in Traditional Chinese (Taiwan usage), through an in-session review loop with two independent subagent Reviewers (fidelity against the notes, then readability) that read files from disk rather than having them pasted in. This skill is fully self-contained: no external spec document is needed or will be supplied to run it -- this file plus references/ is the complete, current spec.
---

# Blog Writer (Step 2: Writer + Reviewers)

The complete spec for Step 2 of this repo's pipeline (see the repo
`CLAUDE.md`). This file plus `references/` is all there is.

The goal is an article that is **easy to read** (structure, order, layout),
**easy to understand** (logic, explanation), and **loses nothing** from the
notes. Reviewer B guards the last; Reviewer A guards the first two.

## Hard rules

1. **Never read the source PDF or open any image.** The only sources of fact
   are the notes/chatlog file and the `caption` / `page` / `type` /
   `nearby_text` fields of `image-manifest.json`. If the notes are
   underspecified, write around the gap and flag it; don't peek.
2. **Prose is Traditional Chinese, Taiwan usage (台灣繁體中文)**: headings,
   alt text and visible captions included. The one exception is each
   `figure-map` entry's `references_manifest_caption`, verbatim from the
   manifest.
3. **Write like a Taiwanese AI/software engineer wrote it by hand**
   (`references/writing-style.md`).
4. **The reader has never read the paper.** When unsure whether something
   needs explaining, explain it.
5. **Preserve the notes' depth; solve readability with structure, not
   deletion.** Carry forward every explanation, worked example, caveat and
   aside, and especially anything the notes flag as independently valuable.
   If the notes read as two parts (the paper, and standalone lessons), the
   article visibly carries both. The only cuts allowed are true redundancy
   (the same content kept once, in full, somewhere) and the notes' own
   meta-commentary about note-taking.
6. **Only the figures and tables the notes mention.** A manifest entry the
   notes never refer to stays out of the article, however good its caption.

## Inputs

In `<dir>/`: the notes/chatlog file (`.txt`, `.md`, `.json`; detect by what's
there) and `assets/image-manifest.json` (read only `id` / `caption` / `page` /
`type` / `nearby_text`).

**No manifest but a source PDF:** stop and run Step 1
(`pdf-figure-table-parser`) first. **No PDF, or Step 1 extracted nothing
usable:** write with figures described in prose (never an invented id), an
empty `figure-map` (`` ```figure-map\n[]\n``` ``), and this exact first line:
`<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match manually -->`.
Say which case applies when you report.

## Workflow

1. **Read the notes in full.** Note the explicit figure/table callouts (the
   shortlist, rule 6) and any element that didn't survive as text (an
   `[embedded content: ...]` diagram, a lost image). Rebuild such an element
   only from what the notes state elsewhere, never by guessing what it showed,
   and list it in the PR Notes.

2. **Match callouts to manifest ids** by caption content, never by assuming
   the numbers line up.

3. **Write the first draft** to the bar in `references/writer-reviewer-spec.md`:
   - a concise `## 前言` right after the title and a `## 結論` (a quick recap)
     as the last section, with any concept deep-dive, glossary or
     limitations section placed before it;
   - exactly one `#`; independent themes at `##` with sub-topics at `###`;
   - formal definitions and every symbol in LaTeX (`writing-style.md`);
   - figures as `![alt](img-00N)` plus an italic caption, and paper data
     tables as Markdown tables with the same kind of caption, numbered in
     article order (`references/figure-map-schema.md`);
   - the notes' provenance labels (paper fact / inference / made-up example /
     unclear) kept, in one consistent form (`writing-style.md`);
   - a single trailing `figure-map` block; no Hugo front matter or shortcodes.

4. **Self-check before any review.**
   ```bash
   python .claude/skills/blog-writer/scripts/verify_article.py <dir>/article.md --manifest <dir>/assets/image-manifest.json
   python .claude/skills/blog-writer/scripts/coverage_check.py <dir>/<notes> <dir>/article.md [--skip-heading 索引]
   ```
   Fix every `verify_article.py` warning. For each coverage item, either add
   it or note why it is left out (reworded, meta-commentary); keep these
   notes for the review responses. Then read the draft once against this list,
   which is what reviewers flagged most often:
   - the same content explained in full twice (keep one, point to it);
   - a term defined two different ways, or used before its definition;
   - a pointer to a section by anything other than its exact heading;
   - a claim with no concrete example; an A/B contrast left as prose;
   - the same hedge or opener repeated 3+ times.

5. **Review, in two phases.** Both reviewers are fresh subagents with no
   memory of this conversation, given file paths and the prompts in
   `references/reviewer-prompts.md`. Never paste the article into a prompt.

   - **Phase 1, Reviewer B (fidelity), up to 3 rounds.** Round 1 reads the
     notes, the article and the coverage report. Stop on
     `FIDELITY_APPROVED_NO_CHANGES`. After this phase the content is settled.
   - **Phase 2, Reviewer A (readability), up to 3 rounds,** a new subagent.
     Round 1 reads the whole article (it must meet the text cold). Stop on
     `REVIEW_APPROVED_NO_CHANGES`.
   - **Final fidelity check,** only if a change for A deleted or reworded a
     fact: one delta for all of A's rounds, sent to B. It doesn't count
     toward B's 3 rounds.

   **Later rounds read a delta, not the article.** Before editing, copy
   `article.md` to the scratchpad (`article.r<N>.md`). After editing, write a
   responses file (one line per finding: `B3 fixed, see change C`, or why it
   was left, and for every deletion where that content now lives), then:
   ```bash
   python .claude/skills/blog-writer/scripts/make_delta.py <scratch>/article.r<N>.md <dir>/article.md \
     --out <scratch>/delta.r<N>.md --responses <scratch>/responses.r<N>.md \
     --manifest <dir>/assets/image-manifest.json [--notes <dir>/<notes>]
   ```
   Resume the same reviewer with `SendMessage` and the delta path. The
   script marks the delta FULL RE-READ NEEDED when more than 30% of
   paragraphs changed or a `##` section was added, removed, renamed or moved;
   the reviewer then reads the whole article. Pass `--notes` for B's deltas.

   **When the reviewers pull in opposite directions,** B wins on what the
   article says and A wins on how and where it says it. Merging duplicates is
   fine as long as the content keeps one full home; that is not an omission.

   **Stopping early:** if a round's remaining items are a few small,
   mechanical fixes, apply them and stop instead of spending another round,
   and say so in the PR Notes. After 3 rounds, keep the latest version.

   If no subagent tool is reachable, do each review yourself from a fresh
   read of the files, with the same prompts and verdicts, and state the
   deviation in the report.

6. **Verify.** `verify_article.py` passes (omit `--manifest` for the
   `NO-MANIFEST` case).

## Definition of done

- `article.md` passed both reviews (or their rounds ran out), reflects the
  notes honestly (caveats included) and keeps their substance.
- Every body image `src` is a manifest `id` the notes mention (or the file
  carries the `NO-MANIFEST` note), the `figure-map` is valid and complete, and
  there is no Hugo syntax. `verify_article.py` passes.
- The topic is moved and the task finished per the repo `CLAUDE.md`. The PR
  Notes list: rounds per reviewer and any early stop; coverage items left out
  on purpose, with reasons; rebuilt non-text elements from step 1; unreferenced
  manifest entries.

## Files

```
blog-writer/
├── SKILL.md
├── references/
│   ├── writer-reviewer-spec.md   writing-quality bar
│   ├── reviewer-prompts.md       Reviewer B and A prompts, delta-round and final-check messages
│   ├── figure-map-schema.md      image/table reference convention + figure-map schema
│   └── writing-style.md          Traditional Chinese (Taiwan) voice guide
└── scripts/
    ├── verify_article.py         structural/format checks
    ├── coverage_check.py         notes numbers/terms missing from the article
    └── make_delta.py             delta file for a reviewer's later rounds
```
