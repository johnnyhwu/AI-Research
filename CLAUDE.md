# AI-Research

This repo is the **content repo** (`CONTENT_REPO`) for a 3-step blog-writing
pipeline. It hosts source material (papers) and the output of Step 1 and
Step 2 below. A separate Hugo repo (`HUGO_REPO`, not this repo) is where
Step 3 turns an approved article into a published post — nothing in this
repo talks to Hugo directly.

| Step | Role | Runs in this repo? | Skill |
|---|---|---|---|
| 1 | Writer + Reviewer — turns a source doc + discussion into `article.md` | Yes | `.claude/skills/blog-writer/` (see below — may not exist yet) |
| 2 | Parser — extracts figures/tables from the PDF into an image manifest | Yes | `.claude/skills/pdf-figure-table-parser/` |
| 3 | Publisher — wires `article.md` + manifest + images into a Hugo post | No (separate repo) | n/a |

If you're working in this repo, you are doing Step 1 and/or Step 2 work.
Read this file fully before touching a topic directory — the two steps have
a real ordering dependency (below), and both rely on conventions that aren't
obvious from the files alone.

## Topic directories

Each source document gets its own top-level directory at the repo root —
e.g. `SkillOpt/`. Think of this as playing the role of `docs/<slug>/` from
the pipeline's shared contract, just without a `docs/` prefix: this repo
puts each topic's directory straight at the root.

Expected contents of a topic directory, once both steps have run:

```
<TopicDir>/
  <original-paper>.pdf        # the source PDF -- keep its real filename,
                               # don't require it to be literally "source.pdf"
  <notes-or-chatlog>.<ext>    # the AI-discussion transcript / user's notes on
                               # the paper -- filename and format vary, detect
                               # by what's actually there (.txt, .md, .json)
  assets/
    image-manifest.json       # written by Step 2 (see schema below)
    images/                   # written by Step 2
  article.md                  # written by Step 1
```

**Canonical path for new topics**: put Step 2's output directly at
`<TopicDir>/assets/image-manifest.json` and `<TopicDir>/assets/images/` —
that's what Step 1 expects to find. (`SkillOpt/` itself is a first-cut
exception: its manifest lives at `SkillOpt/parsed/assets/image-manifest.json`
instead, from before this convention was written down. Don't replicate that
extra `parsed/` nesting for new topics.)

## The ordering constraint

Step 2's parse (producing the image manifest) must finish before Step 1
starts writing, because the Writer must only reference figures/tables that
actually got extracted. If you're asked to do both for the same topic, run
Step 2 first. If Step 2 hasn't run yet and you're asked to write the
article anyway, the Writer skill's own fallback applies (write the article,
but reference figures only descriptively in prose, and mark the file with
`<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match
manually -->` at the top) — don't block on this, just don't invent a
manifest that doesn't exist.

## What to do when the user says...

| User says (roughly) | Do this |
|---|---|
| "針對 `<dir>` 開始 parse pdf" / "parse the PDF in `<dir>`" / "extract figures/tables from `<dir>`" | Use the **`pdf-figure-table-parser`** skill against the PDF in `<dir>/`. Output goes to `<dir>/assets/image-manifest.json` + `<dir>/assets/images/` (see canonical path above). |
| "開始產生 blog" / "generate the blog (post) for `<dir>`" / "write the article for `<dir>`" | Use the **Step 1 Writer/Reviewer skill** against `<dir>/`. Check the available-skills list for one covering "Writer + Reviewer loop producing article.md" — it's expected to live at `.claude/skills/blog-writer/` (see note below if it isn't there yet). |
| Ambiguous ("do the pipeline for `<dir>`", no PDF/manifest yet) | Run Step 2 first, then Step 1, per the ordering constraint above. |

**If the Step 1 skill isn't installed yet**: it's meant to be added as a
sibling of `pdf-figure-table-parser` under `.claude/skills/`. If a user asks
you to "generate the blog" and no such skill is present, say so rather than
improvising the Writer/Reviewer loop from memory — the actual spec (writing
quality bar, the Writer⇄Reviewer loop mechanics, the `figure-map` contract)
has more detail than fits here, and is what that skill is meant to encode.

## Global rules that apply to both steps

These come from the pipeline's shared contract and matter regardless of
which step you're doing:

- **Never load image files into context.** Step 2 extracts visuals using
  file/text-level tools only (see the parser skill for how). Step 1 reads
  only the manifest's captions/pages/types/nearby_text — never the image
  files themselves. If you find yourself about to open a PNG or a PDF page
  render "just to check," stop — that defeats the reason this pipeline has
  a separate parsing step at all.
- **Never invent a manifest id.** If an article references a figure/table id
  with no matching manifest entry, that's a bug to surface, not paper over.
- **Prefer the PDF over the chat log/notes for facts.** The notes file is a
  discussion or outline and may contain misreadings; the PDF is the source
  of truth.
- **Fail loud, not silent.** A missing or low-confidence image is worse to
  hide than to flag. Step 2 marks uncertain extractions
  `parser_confidence: "low"`; Step 1 uses the `NO-MANIFEST` note when
  there's nothing to work with. Downstream steps rely on these signals being
  honest.

## image-manifest.json, in brief

Step 2 writes one entry per extracted visual:

```json
{
  "source_pdf": "<TopicDir>/<paper>.pdf",
  "generated_by": "...",
  "images": [
    {
      "id": "img-001",
      "file": "<TopicDir>/assets/images/picture-001.png",
      "type": "figure",
      "page": 5,
      "caption": "Figure 3: ...",
      "nearby_text": "As shown in Figure 3, ...",
      "parser_confidence": "high",
      "table_markdown": "..."
    }
  ]
}
```

`id` is the join key Step 1 reuses directly as the image `src` in
`article.md`, and again in the trailing `figure-map` block. Full field
semantics are in
`.claude/skills/pdf-figure-table-parser/references/image-manifest-schema.md`
— read that, not just this summary, before writing code against the schema.

## article.md, in brief

Step 1's output is a platform-neutral Markdown article: plain prose body,
figures referenced as `![alt](img-00N)` immediately followed by an italic
human-readable caption, and a single fenced ```` ```figure-map ```` block at
the very end (machine-readable, one entry per referenced id, giving Step 3
enough to match ids to real images). No Hugo front matter or shortcodes
belong in this file — that's Step 3's job in the Hugo repo, not this one.
