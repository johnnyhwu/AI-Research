# Writer ⇄ Reviewer spec

The full writing-quality bar. The review loop itself (Reviewer prompt, cycle
limit, resume, fallback) is in `SKILL.md`; the figure conventions are in
`figure-map-schema.md`.

## Writing quality bar

- **A narrative, not a transcript.** Read the whole notes file first, decide
  the actual story (what problem, what key idea, why a reader should care),
  and write toward it instead of replaying the chat turn by turn or
  section-header by section-header.
- **Concise 前言 and 結論.** A `## 前言` right after the title that orients the
  reader in a couple of short paragraphs, and a `## 結論` last that quickly
  recaps the takeaways. Neither should run as long as a body section.
- **Completeness over brevity: long is fine, thin is not.** Carry forward
  everything substantive in the notes (explanations, worked examples, caveats,
  asides, anything flagged as independently valuable even when tangential).
  Don't shorten a section just because it is "long enough". What counts as
  rambling, and gets cut, is restating a point or content-free transitions,
  not depth. Assume a competent engineer willing to read a genuinely thorough
  piece who is not an expert in this paper.
- **A coverage pass before review.** Walk the notes' outline and check where
  each major point landed. Anything missing needs a reason that survives
  scrutiny (true redundancy); "too long" and "didn't fit the arc" don't.
- **Explain from first principles.** Plain language before symbols and terms of
  art. Prioritize what is practically useful to an engineer, not just what is
  novel.
- **Honest, not promotional.** Include the limitations, caveats and open
  questions the notes surfaced, usually near the end as a distinct "where this
  could bite you" section.
- **Paraphrase and attribute.** Don't reproduce the source verbatim.
- **Every claim traces to the notes.** If the notes don't cover something,
  say it another way the notes do support, or leave it out. Don't fill gaps
  from general knowledge of the topic, and don't guess.

## Figures and tables

- Reference a visual only where it supports the surrounding text, at the point
  it's relevant, not batched at the end and not just because it is in the
  manifest. Explicit callouts in the notes ("建議在此處貼上 Figure 1") are the
  intended shortlist; match them to the manifest by caption content, not by
  assuming the numbers line up 1:1.
- Each referenced id gets an alt, a visible caption line, and a `figure-map`
  entry. Never reference an id without a manifest entry. Details and
  numbering: `figure-map-schema.md`.
- No Hugo front matter, shortcodes or other platform syntax. The only
  non-prose element is the single trailing `figure-map` block.

## Reviewer role

The Reviewer is an ordinary web reader with no prior knowledge of the paper
who sees only `article.md` (no PDF, notes or manifest). Its job is strictly
**readability**, not factual accuracy, and it ignores the `figure-map` block.
The checklist it runs is the prompt in `SKILL.md`, step 4; the voice rules it
enforces are in `writing-style.md`.
