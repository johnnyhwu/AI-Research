# AI-Research

This repo is the **content repo** (`CONTENT_REPO`) of a 4-step blog-writing
pipeline. It holds source papers plus the output of Steps 1 and 2. Steps 3 and
4 turn an approved article into a Hugo post in a separate repo (`HUGO_REPO`,
`johnnyhwu/johnnyhwu.github.io`, whose `CLAUDE.md` describes them); nothing
here talks to Hugo.

| Step | Role | Runs here? | Skill |
|---|---|---|---|
| 1 | Parser: PDF figures/tables → image manifest | Yes | `.claude/skills/pdf-figure-table-parser/` |
| 2 | Writer + two Reviewers: notes + manifest → `article.md` | Yes | `.claude/skills/blog-writer/` |
| 3 | Planner + Reviewers: `article.md` → a reader-friendly plan (zh + en JSON) | No | n/a |
| 4 | Publisher: plan + manifest + images → Hugo post | No | n/a |

The two skills are self-contained and the sole source of truth for how to do
each step; no other spec will be supplied. The `NO-MANIFEST` marker line
(checked by `verify_article.py`) says "Step 3" for "the Hugo side"; it is left
as is on purpose, because the script matches it exactly.

**Step 1 always finishes before Step 2 starts.** If asked to write a topic
that has a PDF but no manifest, run Step 1 first, then write. Don't ask, don't
degrade.

## Separation between the steps

- **Step 1 never opens the notes/chatlog.** It judges which visuals matter
  from the paper's own captions. The notes describe what a human wants
  *written*, which is Step 2's concern.
- **Step 2 never reads the source PDF and never opens an image.** The notes
  are its only source of facts; the manifest's text fields its only figure
  context. It uses only the figures and tables the notes mention.
- **Image pixels stay out of the main context** in both steps; a visual check
  goes through a subagent on downscaled copies.
- **Fail loud.** A manifest id that doesn't exist is a bug to surface, never
  to paper over.

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
currently sits (no `parsed/` level; `done/published/SkillOpt/` is the one
legacy exception). Many older `done/` topics predate the PDF pipeline:
`article.md` plus a hand-curated `assets/`, no PDF, `"source_pdf": null`.
Treat them as done. Their `feature-image-*.jpg` has no manifest entry on
purpose; Step 4 uses it as `featuredImage`.

### Moving a topic between buckets

1. Step 2 finishes → `git mv in-progress/<TopicDir> done/unpublished/<TopicDir>`,
   as part of that task.
2. Step 4 publishes → `git mv done/unpublished/<TopicDir> done/published/<TopicDir>`.
   The `hugo-publisher` skill in the other repo opens this companion PR
   itself (branch `claude/mark-<topic>-published`).

The manifest's `source_pdf` and every `images[].file` are repo-relative paths
baked in at parse time, and `git mv` doesn't rewrite them. After every move,
rewrite their bucket prefix to `<new-bucket>/<TopicDir>/...`, then re-run
`verify_manifest.py`. When re-parsing a topic that already sits in `done/`,
pass `--out-dir`/`--source-pdf-repo-path` with the bucket it is *already* in.

Scripts run with `uv run python ...` from the repo root (deps and Python
version live in `pyproject.toml`). On `ModuleNotFoundError`, run `uv sync`.
Don't create virtual environments elsewhere.

## What to do when the user says...

| User says (roughly) | Do this |
|---|---|
| "針對 `<dir>` 開始 parse pdf" / "extract figures/tables from `<dir>`" | `pdf-figure-table-parser` on the PDF in `<dir>/` (`in-progress/`, or `done/...` when re-parsing). Output to `<dir>/assets/`. |
| "開始產生 blog" / "write the article for `<dir>`" | No manifest but a PDF → Step 1 first. Then `blog-writer` on `in-progress/<dir>/`; move to `done/unpublished/`, fix manifest paths, finish per "Finishing a task". |
| "開始處理 `<dir>`" / ambiguous ("do the pipeline for `<dir>`") | Step 1, then Step 2. |
| "哪些文章可以發布了？" / "what's ready to publish?" | List `done/unpublished/`. |
| "`<dir>` 已經發布了" / "mark `<dir>` as published" | `git mv` to `done/published/`, fix manifest paths, re-run `verify_manifest.py`. |

## Finishing a task

When the work is done and verified, publish it without asking:

1. Branch off up-to-date `main`: `claude/<topic-slug>-article` for a new
   article, `claude/mark-<topic-slug>-published` for a publish move. Never
   commit to `main`.
2. `git add` only the files this task touched (the topic directory). Other
   untracked topic directories belong to someone else's in-flight work.
3. Commit as `Add <TopicDir> article (parse + write), move to unpublished`
   (adapt the verb for other tasks).
4. Push and open the PR with `gh pr create --base main`. The body has a
   `## Summary` (what ran, parser flags or overrides used) and a `## Notes`
   section (low-confidence crops, plus the items `blog-writer`'s
   "Definition of done" lists).
5. Report the PR URL.
