# AI-Research

This repo is the **content repo** (`CONTENT_REPO`) of a 4-step blog-writing
pipeline. It holds source papers plus the output of Steps 1 and 2. Steps 3 and
4 turn an approved article into a Hugo post in a separate repo (`HUGO_REPO`,
`johnnyhwu/johnnyhwu.github.io`); nothing here talks to Hugo.

| Step | Role | Runs here? | Skill |
|---|---|---|---|
| 1 | Parser: PDF figures/tables → image manifest | Yes | `.claude/skills/pdf-figure-table-parser/` |
| 2 | Writer + Reviewer: notes + manifest → `article.md` | Yes | `.claude/skills/blog-writer/` |
| 3 | Planner + Reviewers: `article.md` → a reader-friendly plan (zh + en JSON) | No | n/a |
| 4 | Publisher: plan + manifest + images → Hugo post | No | n/a |

Steps 3 and 4 both run in the Hugo repo (`HUGO_REPO`'s `CLAUDE.md` describes them). The Writer skill's
files and the `NO-MANIFEST` marker line (checked by `verify_article.py`) still say "Step 3" for "the Hugo
side"; read that as Steps 3 and 4. The marker text is left as is on purpose, because the script matches it exactly.

Working here means doing Step 1 and/or 2. **Step 1 always finishes before
Step 2 starts.** The two skills are self-contained and the sole source of
truth for how to do each step; no other spec will be supplied, so don't wait
for or ask for one.

## Topic directories

Each source document gets one directory under one of three buckets. A topic
under `done/` sits **two** levels down (`done/published/SkillOpt/`, never
`done/SkillOpt/`).

- **`in-progress/<TopicDir>/`**: no `article.md` yet. New topics start here.
- **`done/unpublished/<TopicDir>/`**: `article.md` exists, no Hugo post yet.
  This is the publishing queue: "what's ready to publish?" means list this
  bucket.
- **`done/published/<TopicDir>/`**: a Hugo post exists. Touch only to fix an
  already-published post.

Expected contents once both steps have run:

```
<bucket>/<TopicDir>/
  <paper>.pdf               # source PDF, real filename kept
  <notes>.<ext>             # discussion notes/chatlog (.md/.txt/.json), detect by what's there
  assets/image-manifest.json, assets/images/    # Step 1
  article.md                                    # Step 2
```

Step 1 writes straight to `<TopicDir>/assets/` in whichever bucket the topic
currently sits (don't add a `parsed/` level; `done/published/SkillOpt/` is the
one legacy exception). Many older `done/` topics predate the PDF pipeline:
`article.md` plus a hand-curated `assets/`, no PDF, `"source_pdf": null`.
Treat them as done. Their `feature-image-*.jpg` in `assets/images/` has no
manifest entry on purpose; Step 4 uses it as `featuredImage`.

### Moving a topic between buckets

1. Step 2 finishes → `git mv in-progress/<TopicDir> done/unpublished/<TopicDir>`,
   as part of that task.
2. Step 4 publishes → `git mv done/unpublished/<TopicDir> done/published/<TopicDir>`.
   The `hugo-publisher` skill in the other repo opens this companion PR
   itself (branch `claude/mark-<topic>-published`).

`git mv` doesn't rewrite file contents, and the manifest's `source_pdf` and
every `images[].file` are repo-relative paths baked in at parse time. After
every move, rewrite their bucket prefix to `<new-bucket>/<TopicDir>/...`, then
re-run `verify_manifest.py`. When re-parsing a topic that already sits in
`done/`, pass `--out-dir`/`--source-pdf-repo-path` with the bucket it is
*already* in and there is nothing to fix up.

`verify_manifest.py` needs `pymupdf`. On `ModuleNotFoundError`, run `uv sync`
from the repo root (deps and Python version live in `pyproject.toml`; run
scripts with `uv run python ...`). Don't create virtual environments elsewhere.

## The ordering constraint

The Writer may only reference figures that were actually extracted. **If asked
to write a topic that has a PDF but no manifest, run Step 1 first, then write.
Don't ask, don't degrade.** Writing first means rewriting the article once the
manifest exists (`blog-writer`'s SKILL.md has the full cost).

The `NO-MANIFEST` fallback (figures referenced descriptively in prose, file
marked `<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match
manually -->` on line 1) is only for topics where a manifest is *not
achievable*: no source PDF at all, or Step 1 ran and genuinely extracted
nothing usable (e.g. a scanned PDF). Say which case applies when reporting.
Never invent a manifest or reference an id that has no entry.

## What to do when the user says...

| User says (roughly) | Do this |
|---|---|
| "針對 `<dir>` 開始 parse pdf" / "extract figures/tables from `<dir>`" | `pdf-figure-table-parser` on the PDF in `<dir>/` (`in-progress/`, or `done/unpublished/` / `done/published/` when re-parsing). Output to `<dir>/assets/`. |
| "開始產生 blog" / "write the article for `<dir>`" | No manifest but a PDF → Step 1 first. Then `blog-writer` on `in-progress/<dir>/`; when `article.md` is written, move to `done/unpublished/`, fix manifest paths, and finish per "Finishing a task". |
| Ambiguous ("do the pipeline for `<dir>`") | Step 1, then Step 2. |
| "哪些文章可以發布了？" / "what's ready to publish?" | List `done/unpublished/`. |
| "`<dir>` 已經發布了" / "mark `<dir>` as published" | `git mv` to `done/published/`, fix manifest paths, re-run `verify_manifest.py`. |

## Finishing a task

When the work is done and verified, publish it without asking:

1. Branch off up-to-date `main`: `claude/<topic-slug>-article` for a new
   article, `claude/mark-<topic-slug>-published` for a publish move. Never
   commit to `main`.
2. `git add` only the files this task touched (the topic directory). Other
   untracked topic directories belong to someone else's in-flight work; leave
   them out.
3. Commit as `Add <TopicDir> article (parse + write), move to unpublished`
   (adapt the verb for other tasks).
4. Push and open the PR with `gh pr create --base main`. The body has a
   `## Summary` (what ran, key parser flags or overrides used) and a
   `## Notes` section (unreferenced manifest entries, low-confidence crops,
   skipped review cycles, anything the reviewer should know).
5. Report the PR URL.

## Global rules for both steps

- **Keep image pixels out of the main context.** Step 1 judges crops with
  text signals first (bounding boxes, captions, sizes, warnings). When a crop
  looks wrong, or the parser skill names a risk that text can't catch, check it
  visually: `make_review_thumbs.py` writes downscaled copies and a subagent
  looks at them and reports problems as text. Never open a full-size PNG or a
  rendered PDF page in the main session. **Step 2 never opens any image**; it
  reads only the manifest's `caption`/`page`/`type`/`nearby_text`.
- **Step 2 never reads the source PDF.** The notes/chatlog is the sole source
  of facts for `article.md`, and the manifest text fields the sole source of
  figure context. This is a standing house rule. Step 1, by contrast, reads
  the PDF directly; that is its whole job.
- **Step 1 never opens the notes/chatlog.** It reads the PDF's own structure
  (captions, drawings, embedded images). The notes describe what a human wants
  *written*, which is Step 2's concern. Use the paper's captions to judge which
  figures matter.
- **Never invent a manifest id.** An article referencing an id with no
  manifest entry is a bug to surface, not paper over.
- **Fail loud, not silent.** Step 1 marks uncertain extractions
  `parser_confidence: "low"`; Step 2 uses the `NO-MANIFEST` note when there is
  nothing to work with. Downstream steps rely on these signals being honest.

## Manifest and article, in brief

`image-manifest.json` has one entry per extracted visual, keyed by `id`
(`img-001`, ...), with `file`, `type`, `page`, `caption`, `nearby_text`,
`parser_confidence` and optionally `table_markdown`. The `id` is the join key:
Step 2 uses it as the image `src` and in the `figure-map` block; Steps 3 and 4
resolve it to a real path. Field semantics:
`.claude/skills/pdf-figure-table-parser/references/image-manifest-schema.md`.
Read that before writing code against the schema.

`article.md` is platform-neutral Markdown: prose body, figures as
`![alt](img-00N)` each followed by an italic caption, and one trailing
```` ```figure-map ```` block. No Hugo front matter or shortcodes (Step 4's
job). **The prose is Traditional Chinese, Taiwan usage (台灣繁體中文)**,
headings, alt text and captions included, written for a reader who has never
seen the paper. Only each `figure-map` entry's `references_manifest_caption`
stays verbatim in the manifest's language. Voice, structure and figure
conventions: `blog-writer/references/writing-style.md` and
`figure-map-schema.md`.
