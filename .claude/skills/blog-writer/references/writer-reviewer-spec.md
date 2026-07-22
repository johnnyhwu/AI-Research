# Writer ⇄ Reviewer spec (full detail)

This is the full version of the quality bar and loop mechanics summarized in
`SKILL.md`. There is no more complete version elsewhere — treat this as the
authoritative spec, not a summary of some other document.

## Writing quality bar

The article is the actual thing an end reader will see. Hold this bar:

- **Structure around a narrative, not a transcript.** Do not replay the
  notes/chat log turn by turn or section-header by section-header. Read the
  whole thing first, decide what the actual story is (what problem does this
  solve, what's the key idea, why should a reader care), and write toward
  that arc.
- **Not a firehose, not a haiku.** Avoid rambling and avoid burying the
  point, but also avoid being so terse a newcomer can't follow. Assume an
  interested reader who is *not* an expert in this specific paper, but is a
  competent engineer in general.
- **Explain methods from first principles.** Put any necessary math or
  jargon into plain language before (or instead of) symbols/terms of art.
  Prioritize what's practically useful to an engineer reading this, not just
  what's novel about the paper.
- **Be honest, not promotional.** If the notes surfaced real limitations,
  caveats, or open questions about the paper/method, include them — usually
  near the end, as a distinct "here's where this could bite you in practice"
  section. Don't default to uncritical praise just because the notes are
  enthusiastic.
- **Don't reproduce the source verbatim.** Paraphrase in your own words and
  attribute it to the paper where relevant; lean on the (later-embedded)
  figures rather than quoting large blocks of text.
- **Every claim of fact traces back to the notes/chatlog**, per this skill's
  hard rule against reading the PDF. If the notes don't cover something you
  want to say, either find another way to say something the notes *do*
  support, or leave it out — don't fill the gap from general knowledge of
  the paper's topic area, and don't guess.

## Figure/table references

Follow this convention exactly (full schema in `figure-map-schema.md`):
- In the body: `![<alt>](<manifest-id>)` followed immediately by an italic
  human-readable caption line.
- For each referenced id, write a concise **alt** (describes the visual's
  content, not "image of figure 3"), a visible **caption** line, and a
  corresponding entry in the end-of-file `figure-map` block.
- Reference a visual only where it genuinely supports the surrounding text,
  at the point it's relevant — not batched at the end, and not just because
  it exists in the manifest. If the notes explicitly flag certain
  figures/tables as ones to include (this repo's source notes often do,
  e.g. "建議在此處貼上 Figure 1"), that's a strong signal of the intended
  shortlist — cross-check those callouts against the manifest by caption
  content, not by assuming the numbering lines up 1:1.
- Never reference an id that has no manifest entry.

Keep the body free of Hugo front matter, shortcodes, or any
platform-specific syntax. That is Step 3's job, in the separate Hugo repo.
The only non-prose element allowed is the single `figure-map` fenced block
at the very end.

## The Writer ⇄ Reviewer loop

You play **both** roles, but the Reviewer role runs as an independent
subagent (see `SKILL.md`'s workflow step 4) rather than you switching hats
in the same context — this keeps the Reviewer honestly blind to everything
except the file on disk, the same way a real naive reader would be.

### Reviewer role — definition

When acting as Reviewer (or when writing the subagent prompt that assigns
this role), the persona is **an ordinary web reader with no prior knowledge
of this paper**, who **cannot see** the source PDF, the notes, or the
manifest — only `article.md`. The job is strictly **readability**, not
correctness (a naive reader can't verify facts, so don't pretend to).
Assess:
- Is it easy to follow? Does the arc make sense to a newcomer?
- Is the pacing right — no rambling, no skipped leaps that lose a beginner?
- Layout/formatting: headings, flow, figure placement reading naturally.
- Obvious typos, awkward phrasing, self-contradiction, broken sentences.
- Since this repo requires Traditional Chinese (Taiwan usage): does
  anything read as English, Simplified Chinese phrasing, or stiff
  AI-translated Chinese? That's in scope — it's a readability/authenticity
  defect, not a factual one.

Do **not** comment on factual accuracy vs. the source (the Reviewer can't
see it, so it shouldn't pretend to) and do **not** comment on the trailing
`figure-map` block (it's metadata for Step 3, not something a reader sees).

### Loop mechanics

1. Writer produces `article.md`.
2. Reviewer (subagent) reads **only** `article.md` from disk and returns
   concrete, actionable feedback — or approves.
3. **Early exit:** if the article has no issues worth fixing, the Reviewer's
   entire output must be the single line `REVIEW_APPROVED_NO_CHANGES` and
   nothing else. Emit this token only when there are zero change requests.
   If there's any real suggestion, give it and do not emit the token.
4. **Don't manufacture work.** If the only findings are nitpicks that
   wouldn't bother a real reader, approve instead. Padding feedback to look
   thorough just wastes a review cycle.
5. Writer revises `article.md` based on the feedback, in place, at the same
   path.
6. Repeat at most **3** full Writer→Reviewer cycles. Stop early on
   `REVIEW_APPROVED_NO_CHANGES`. After 3 cycles, keep the latest version
   regardless of remaining feedback.

## Output

- `<dir>/article.md`, containing the article body + the trailing
  `figure-map` block.
- Do not modify anything under `<dir>/assets/` — that's Step 2's territory.

## Definition of done

- `article.md` exists, reads well to a naive reader, and honestly reflects
  the notes/chatlog.
- Every body image `src` is a manifest `id` (or the file carries the
  `NO-MANIFEST` note and references figures only in prose).
- The trailing `figure-map` block is valid JSON and covers every referenced
  id.
- No Hugo-specific syntax anywhere in the file.
