# AI-Research

This repo is the **content repo** (`CONTENT_REPO`) for a 3-step blog-writing
pipeline. It hosts source material (papers) and the output of Step 1 and
Step 2 below. A separate Hugo repo (`HUGO_REPO`, not this repo) is where
Step 3 turns an approved article into a published post — nothing in this
repo talks to Hugo directly.

| Step | Role | Runs in this repo? | Skill |
|---|---|---|---|
| 1 | Writer + Reviewer — turns discussion notes + an image manifest into `article.md` | Yes | `.claude/skills/blog-writer/` |
| 2 | Parser — extracts figures/tables from the PDF into an image manifest | Yes | `.claude/skills/pdf-figure-table-parser/` |
| 3 | Publisher — wires `article.md` + manifest + images into a Hugo post | No (separate repo) | n/a |

If you're working in this repo, you are doing Step 1 and/or Step 2 work.
Read this file fully before touching a topic directory — the two steps have
a real ordering dependency (below), and both rely on conventions that aren't
obvious from the files alone.

## Topic directories

Each source document gets its own top-level directory at the repo root —
e.g. `SkillOpt/`. Think of this as playing the role of `docs/<slug>/` from
the broader pipeline's usual layout, just without a `docs/` prefix: this
repo puts each topic's directory straight at the root.

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
| "開始產生 blog" / "generate the blog (post) for `<dir>`" / "write the article for `<dir>`" | Use the **`blog-writer`** skill (`.claude/skills/blog-writer/`) against `<dir>/`. |
| Ambiguous ("do the pipeline for `<dir>`", no PDF/manifest yet) | Run Step 2 first, then Step 1, per the ordering constraint above. |

Both skills are self-contained and are the sole source of truth for how to
do Step 1 / Step 2 in this repo. No spec document will be supplied alongside
a task — don't wait for one, and don't ask for one. Whatever material was
originally used to write a skill has already been folded into that skill's
`SKILL.md` + `references/`; treat the skill itself as current and complete,
not something to reconstruct from memory or from an outside document.

## Global rules that apply to both steps

These matter regardless of which step you're doing:

- **Never load image files into context.** Step 2 extracts visuals using
  file/text-level tools only (see the parser skill for how). Step 1 reads
  only the manifest's captions/pages/types/nearby_text — never the image
  files themselves. If you find yourself about to open a PNG or a PDF page
  render "just to check," stop — that defeats the reason this pipeline has
  a separate parsing step at all.
- **Step 1 never reads the source PDF either — notes/chatlog only.** Treat
  the topic dir's notes/chatlog file as the sole source of facts for
  `article.md`, and the manifest's `caption`/`page`/`type`/`nearby_text`
  fields as the sole source of figure context. This is a deliberate,
  standing house rule for this repo, established through direct instruction
  — it keeps Step 1 fast and keeps the PDF-reading work concentrated in Step
  2, where it belongs. Step 2, by contrast, reads the PDF directly — that's
  its entire job.
- **The same boundary cuts the other way: Step 2 has no business opening
  the notes/chatlog file either.** Step 2's job is to read the PDF's own
  structure (captions, drawings, embedded images) and produce the manifest
  — the discussion notes describe *what a human wants written about the
  paper later*, which is Step 1's concern, not Step 2's. Opening it "just to
  understand the paper better" doesn't change what gets extracted and only
  burns context reading a file (often hundreds of lines) that this step has
  no use for. If you need to sanity-check which figures/tables actually
  matter, that's what the paper's own captions are for.
- **Never invent a manifest id.** If an article references a figure/table id
  with no matching manifest entry, that's a bug to surface, not paper over.
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

**Write the prose body in Traditional Chinese, Taiwan usage (台灣繁體中文)**
— not English, not Simplified Chinese. This applies to headings, alt text,
and visible captions too. It should also read like a Taiwanese AI/software
engineer wrote it by hand for a technical audience, not like generic
AI-generated writing — the `blog-writer` skill's `references/writing-style.md`
has the concrete dos/don'ts. The one thing that stays in English verbatim is
each `figure-map` entry's `references_manifest_caption` — it has to match
the manifest's own (English, paper-native) caption text exactly, since
that's what Step 3 uses to confirm the join.

The target reader has never read the source paper. Readability and
correctness for that reader matter more than brevity or cleverness — when
in doubt, explain rather than assume.
