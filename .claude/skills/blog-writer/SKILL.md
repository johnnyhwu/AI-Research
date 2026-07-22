---
name: blog-writer
description: Use this skill whenever you need to write or revise article.md for a topic directory in this repo's blog-writing pipeline (Step 1 -- Writer + Reviewer), triggered by phrases like "開始產生 blog", "generate the blog/post for <dir>", "write the article for <dir>", or "幫 <dir> 寫文章". Turns a topic directory's discussion-notes/chatlog file (never the source PDF, never any image) plus its image-manifest.json's text fields (caption/page/type/nearby_text only) into a polished, platform-neutral article.md written in Traditional Chinese (Taiwan usage), through an in-session Writer <-> Reviewer loop where the Reviewer runs as an independent subagent that reads article.md from disk rather than having it pasted in. This skill is fully self-contained: no external spec document is needed or will be supplied to run it -- this file plus references/ is the complete, current spec.
---

# Blog Writer (Step 1: Writer + Reviewer)

## Why this skill exists

This is the complete, current spec for Step 1 of this repo's 3-step blog
pipeline (see the repo's `CLAUDE.md` for the pipeline overview). No external
document backs this up and none will be supplied alongside a future task —
this `SKILL.md` plus its `references/` docs is the whole spec. A future
invocation of this skill needs nothing beyond this folder plus the topic
directory itself.

## The hard rules (read before doing anything else)

1. **Never read the source PDF, and never open any image file, at any point
   in this workflow.** Not "just to double check" a fact, not "just to see"
   a figure. Fact-checking against the PDF and rendering crops is Step 2's
   job, already done by the time this skill runs. Your only sources of fact
   are:
   - the topic directory's notes/chatlog file, and
   - the `caption` / `page` / `type` / `nearby_text` **text fields** of
     `image-manifest.json` (never the `file` path's actual image bytes).

   This is stricter than the generic pipeline contract, which technically
   permits the Writer to read the PDF's text. In this repo, don't — it's a
   deliberate, standing house rule established by direct user instruction,
   not an oversight. If you find yourself reaching for the PDF or a PNG "just
   to confirm," stop; that impulse means the notes file was underspecified,
   not that you should route around the rule. Write around the gap instead
   (see the `NO-MANIFEST`-style honesty pattern below — the same "flag it,
   don't fake it" instinct applies to any fact the notes don't cover).

2. **Write `article.md`'s prose in Traditional Chinese, Taiwan usage
   (台灣繁體中文)** — not English, not Simplified Chinese, not a mix. This
   covers headings, alt text, and visible image captions. The one exception:
   each `figure-map` entry's `references_manifest_caption` field stays
   verbatim in whatever language the manifest's own caption is in (normally
   English, since it's extracted straight from the paper) — see
   `references/figure-map-schema.md`.

3. **Write like a Taiwanese AI/software engineer wrote it by hand, not like
   generic AI output.** See `references/writing-style.md` for concrete
   dos/don'ts. This matters as much as technical accuracy for this repo's
   purposes — a reader should not be able to tell an LLM wrote this article
   from its prose style alone.

4. **The target reader has never read the source paper.** Readability and
   correctness for that reader outrank brevity or cleverness. When genuinely
   in doubt about whether something needs more explanation, explain it.

## Inputs

For the target topic directory `<dir>/` (see repo `CLAUDE.md` for the
canonical layout):
- `<dir>/<notes-or-chatlog>.<ext>` — the discussion transcript / outline /
  notes about the paper. Format varies (`.txt`, `.md`, `.json`) — detect and
  parse accordingly (`json.load` for JSON, read directly otherwise). This is
  your primary and, per the hard rule above, *only* source of facts.
- `<dir>/assets/image-manifest.json` — normally at this canonical path, but
  check `CLAUDE.md`'s topic-directory section for any documented per-topic
  exception (e.g. `SkillOpt/parsed/assets/image-manifest.json`) before
  assuming the canonical path. Read only `id` / `caption` / `page` / `type` /
  `nearby_text` from each entry.

### If the manifest is missing, empty, or Step 2 hasn't run

Still write the article, but:
- reference figures only **descriptively in prose** ("論文中的延遲對照圖表顯示…"),
  never inventing an id;
- emit an **empty** `figure-map` block (`` ```figure-map\n[]\n``` ``);
- add this exact line as the very first line of the file:
  `<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match manually -->`

This keeps the pipeline unblocked while making the degraded state loud, per
the repo's fail-loud-not-silent rule.

## Workflow

1. **Read the notes/chatlog file in full.** This is where the narrative,
   the emphasis, and — critically — which figures/tables the user actually
   cares about seeing in the article come from. If the notes call out
   specific figures/tables for insertion (they often do, explicitly), that's
   the shortlist of manifest ids worth referencing — don't feel obligated to
   reference every manifest entry just because it exists. A visual earns a
   place in the article by genuinely supporting a paragraph, not by existing.

2. **Read the manifest's text fields** (skip this step per the fallback
   above if there is no manifest). Cross-reference the notes' own callouts
   ("插入 Figure 1 這裡", "圖表對照點 3" etc.) against manifest ids by
   caption content — never by guessing a number.

3. **Write the first draft as Writer.** Hold this quality bar (full detail
   in `references/writer-reviewer-spec.md`):
   - Structure around a narrative arc, not a replay of the chat log turn by
     turn.
   - Explain methods from first principles; plain language before symbols.
   - Be honest about limitations/caveats the notes surfaced — no uncritical
     praise.
   - Paraphrase in your own words; don't reproduce the source verbatim.
   - Reference a visual only where it genuinely helps, at the point it's
     relevant, using the manifest `id` directly as the image `src`:
     `![alt](img-00N)` immediately followed by an italic caption line.
   - No Hugo front matter, shortcodes, or other platform-specific syntax
     anywhere in the file — that's Step 3's job, in a different repo.
   - A single fenced ```` ```figure-map ```` block at the very end (schema in
     `references/figure-map-schema.md`), covering every id referenced in the
     body and nothing else.
   - Everything in Traditional Chinese (Taiwan usage), styled per
     `references/writing-style.md`.

4. **Send it to Reviewer as an independent subagent — by path, not by
   pasting the content.** Spawn a fresh subagent and give it:
   - the exact file path to `article.md`, with an instruction to read it
     itself via its own Read tool;
   - the full Reviewer persona/instructions reproduced below (the subagent
     has no memory of this conversation or this skill, so the instructions
     must be self-contained in the prompt you send it — don't just say "you
     know the drill").

   Never paste the article's content into the subagent prompt yourself —
   that duplicates the exact same text into two contexts for no benefit, and
   the entire reason to use a path is to avoid that.

   Reviewer prompt to send (fill in the real path):
   > Read the file at this exact path and review it: `<path-to-article.md>`
   >
   > Do not read any other file (no PDF, no images, no manifest, no notes
   > file). Adopt the persona of an ordinary web reader with no prior
   > knowledge of the paper, who cannot see the source PDF or any notes —
   > only this file. Your job is strictly READABILITY, not factual
   > correctness (you have no way to verify facts, so don't try). Assess:
   > is it easy to follow for a newcomer, is the pacing right, does
   > layout/figure placement read naturally, and are there typos, awkward
   > phrasing, or self-contradictions? Since this article should be written
   > in Traditional Chinese (Taiwan usage), also flag anything that reads as
   > English, Simplified Chinese, or awkward/AI-sounding translationese —
   > that's a readability/authenticity problem, squarely in scope. Do not
   > comment on the trailing `figure-map` fenced block (metadata for a later
   > step, not something a reader sees).
   >
   > If there's nothing worth fixing, your entire output must be exactly
   > one line: `REVIEW_APPROVED_NO_CHANGES` — emit this only when you have
   > zero change requests. Otherwise, give concrete, actionable feedback
   > (quote the sentence, say what's wrong, say what you'd change) and do
   > not emit that token. Don't manufacture nitpicks that wouldn't actually
   > bother a real reader just to have something to say — approve instead.

5. **Loop.** Apply the Reviewer's feedback as Writer, then send the *same
   file path* back to the *same subagent* (resume it — it already has the
   context of what it flagged; don't spin up a new one each cycle) for
   another pass. Repeat for at most **3** full Writer→Reviewer cycles total.
   Stop early the moment a cycle returns `REVIEW_APPROVED_NO_CHANGES`. After
   3 cycles, keep the latest version regardless.

6. **Verify before calling it done.**
   ```bash
   python .claude/skills/blog-writer/scripts/verify_article.py <dir>/article.md \
     --manifest <dir>/assets/image-manifest.json
   ```
   Checks the `figure-map` block is valid JSON, that its ids exactly match
   the ids referenced in the body (no orphans either direction), that every
   referenced id actually exists in the manifest, that there's no Hugo-style
   `{{< ... >}}` shortcode syntax anywhere, and does a rough CJK-density
   sanity check on the prose (a strong signal the file accidentally came out
   in English). Omit `--manifest` for the `NO-MANIFEST` case — the script
   then just checks the file starts with the required comment and that
   `figure-map` is `[]`.

## Definition of done

- `article.md` exists, reads well to a naive reader, and honestly reflects
  the notes/chatlog (including any limitations/caveats it raised).
- Every body image `src` is a manifest `id` (or the file carries the
  `NO-MANIFEST` note and figures are referenced only in prose).
- The trailing `figure-map` block is valid JSON and covers every referenced
  id, and nothing else.
- No Hugo-specific syntax anywhere in the file.
- The prose is Traditional Chinese, Taiwan usage, and reads like a person
  wrote it — not translationese, not generic AI phrasing.
- `verify_article.py` passes.

## Files in this skill

```
blog-writer/
├── SKILL.md                              (this file)
├── references/
│   ├── writer-reviewer-spec.md           full writing-quality bar + loop mechanics
│   ├── figure-map-schema.md              image reference convention + figure-map schema
│   └── writing-style.md                  Traditional Chinese (Taiwan) voice guide
└── scripts/
    └── verify_article.py                 figure-map / manifest / Hugo-syntax / CJK-density checks
```
