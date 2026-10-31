# Reviewer prompts

Two independent subagents, each with one job. Run them in the order in
`SKILL.md`, step 5: B until the content is settled, then A. Neither ever reads
the source PDF or an image. Paths are passed, never pasted content.

| | Reviewer B: fidelity | Reviewer A: readability |
|---|---|---|
| Reads | notes file, `article.md`, coverage output | `article.md` only |
| Persona | an editor checking the article against the notes | a reader who has never seen the paper |
| Finds | omissions, distortions, unsupported additions, upgraded certainty | anything that makes the article hard to read or follow |

B never judges style; A never judges facts. A must not see the notes: a
reader who knows the source fills in gaps the article leaves open.

## Reviewer B: first round

> Read these files: the notes at `<path-to-notes>`, the article at
> `<path-to-article.md>`, and the coverage report at `<path-to-coverage.txt>`.
> Do not read any other file (no PDF, no images).
>
> The article was written from the notes and must stay faithful to them. You
> check FIDELITY AND COMPLETENESS only, not style or readability. Walk the
> notes section by section and report:
>
> 1. **Omission**: a substantive point, number, example, caveat or aside in
>    the notes with no home anywhere in the article. Saying it once, in a
>    different section or in different words, counts as covered. Work through
>    the coverage report: each listed item is a candidate, so confirm it is
>    really missing, or say it is covered in other words. The notes' own index
>    or meta-commentary about note-taking needs no home.
> 2. **Distortion**: a number, name, setting or claim the article states
>    differently from the notes.
> 3. **Upgraded certainty**: something the notes mark as the note-taker's
>    inference, the paper's speculation ("may"), or unclear, that the article
>    states as fact. Also the reverse: a paper fact presented as a guess.
> 4. **Unsupported addition**: an explanation, number, example or claim in
>    the article that the notes don't support. A made-up illustrative example
>    is fine if the article marks it as made up.
> 5. **Figures**: a figure or table the article embeds that the notes never
>    mention, or one the notes call out that the article leaves out.
>
> Do not comment on the trailing `figure-map` block.
>
> Number your findings `B1`, `B2`, .... For each, give the notes line or quote,
> what the article says (quote it, or "nothing"), the category, and the fix.
> If nothing needs fixing, your entire output must be exactly one line:
> `FIDELITY_APPROVED_NO_CHANGES`. Don't report wording choices that keep the
> meaning.

## Reviewer A: first round

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
> before it is explained; a term defined two different ways; an abstract
> claim about what a method "does" with no concrete example; an A/B
> comparison left as prose instead of a table/parallel bullets; a missing or
> unheaded 前言/結論, an intro that stalls, or a conclusion that re-argues the
> whole piece; reference material (a glossary, concept deep-dives) placed
> between the main argument and the 結論. The article should be Traditional
> Chinese (Taiwan usage), so flag English, Simplified Chinese, or
> AI-sounding translationese, and half-width , ; : ? ! in Chinese prose
> (headings and table cells included; digit-to-digit thousands separators
> and code/URLs are fine). Also flag: (a) more than one top-level `#`, or a
> tangential theme whose sub-topics sit at `##` instead of `###` under one
> `##`; (b) the same blockquote opener/closer, section wrap-up line, heading
> shape or hedge phrase ("我的推論", "論文沒講清楚") repeated 3+ times across
> the whole article (read end to end for this); (c) a formal definition in a
> plain-text code fence instead of LaTeX, or raw notation (`s_v`,
> `π_{t+1}`, `分數 V`) in prose or a table cell outside `$...$`; (d)
> cross-reference problems: a 表 N/圖 N in the prose that doesn't match the
> numbering of the captions, two numbering schemes in play, or a pointer to
> a section that doesn't resolve; (e) the same content explained in full in
> more than one place. Do not comment on the trailing `figure-map` block.
>
> If there's nothing worth fixing, your entire output must be exactly one
> line: `REVIEW_APPROVED_NO_CHANGES`. Otherwise number your findings `A1`,
> `A2`, ... and give concrete, actionable feedback (quote the sentence, say
> what's wrong, say what you'd change); do not emit that token. Don't
> manufacture nitpicks that wouldn't bother a real reader; approve instead.

## Later rounds (either reviewer, resumed with `SendMessage`)

> I revised the article. Read only the delta file at `<path-to-delta.md>`; it
> has my response to each of your findings, the new outline, every changed
> paragraph with the paragraph before and after it, and the mechanical
> checks. If its header says FULL RE-READ NEEDED, re-read `<path-to-article.md>`
> instead. Check that each of your findings is resolved or that the reason
> for leaving it is sound, and that the changes introduced no new problem of
> the kind you review. Same output rule as before.

Reviewer B also checks every "Removed:" block: the delta must say where that
content now lives, and B confirms it from the quoted paragraph.

## Final fidelity check (after A's rounds, only if needed)

Run it when any change made for A deleted or reworded a fact (a number, a
claim, a caveat, an example). Resume B with a delta covering all of A's rounds
(old = the version B approved):

> Reviewer A's rounds changed the article. Read only the delta file at
> `<path-to-delta.md>` and check the changes for omissions, distortions,
> upgraded certainty and unsupported additions, as before. Same output rule.
