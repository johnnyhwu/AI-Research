---
name: pdf-figure-table-parser
description: Use this skill whenever you need to extract figures, tables, or diagrams out of a PDF (especially an academic/arXiv paper) into image files plus a structured manifest, for a downstream step (a writer/summarizer agent, a blog pipeline, a report) that must never load the actual image bytes into its own context. Trigger this whenever the user mentions parsing a paper's PDF for figures/tables, building an image-manifest, or references tools like docling/marker/nougat for PDF visual extraction -- this skill's PyMuPDF-based approach works even when huggingface.co-hosted model downloads are blocked by network/egress policy (a common failure mode for docling and similar ML-model-backed parsers in sandboxed environments), and produces reliable, inspectable crops for born-digital PDFs without any OCR or vision model at all.
---

# PDF Figure/Table Parser (Step 1 in this repo's pipeline)

Step 1 runs *before* `blog-writer` (Step 2), because the Writer may only
reference figures that were extracted. See the repo `CLAUDE.md` for the
pipeline. The skill itself has no dependency on that pipeline.

## Why PyMuPDF and no ML parser

`docling`/`marker`/`nougat` download models from `huggingface.co`, which is
usually blocked by an egress allowlist in sandboxed environments (a policy
denial; don't retry or hunt for a mirror). For a **born-digital PDF** (LaTeX,
Word, etc.; essentially every arXiv paper) none of that is needed: **PyMuPDF**
gives exact text positions, embedded rasters and page rendering from the PDF's
own structure. These scripts find every "Figure N"/"Table N" caption and render
just that visual's region to PNG. No model weights, no network, no OCR.

A scanned PDF (empty or garbled `page.get_text()`, near-zero drawings in
`inspect_pdf.py`) does need OCR; this skill doesn't apply.

## Images stay out of the main context

The point of Step 1 is that later agents never have to load image bytes. So:
judge crops with **text signals** (bounding boxes, caption strings, pixel
sizes, `SUSPECT CROPS`, `verify_manifest.py`), and fix problems with better
heuristics or the override flags, not by looking.

Text can't catch everything. When a crop looks wrong, or the situation is one
of the known blind spots, do a **visual check, never in the main session**:
write downscaled copies and let a subagent look at them (see "Visual check").
Never open a full-size PNG or a rendered PDF page yourself.

Blind spots, none of which trip any automated check:
- a crop that is horizontally too narrow or too wide (outer table columns
  clipped, a neighbour's ink bled in), especially for **short, centered,
  single-line table captions** and for any crop you gave a manual
  left/right override;
- a crop that landed on a neighbouring visual's content;
- a multi-panel figure missing its second half.

## Workflow

1. **Set up once.** `uv sync` from the repo root. Run every script as
   `uv run python .claude/skills/pdf-figure-table-parser/scripts/<name>.py ...`
   from the repo root; the environment is the repo's own `.venv/`.

2. **Dry-run.**
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/inspect_pdf.py in-progress/<Topic>/<paper>.pdf
   ```
   Check the page count, the content area and column edges (if these look
   wrong every crop will be wrong), per-page raster/drawing counts, and the
   detected captions. **A `WARNING: caption numbering has gaps` line means
   captions were filtered out**, nearly always by `--min-caption-width`
   (default 400): a single-column caption in a two-column paper is only
   ~200-230pt wide, and a short centered caption can be narrower still. Re-run
   with e.g. `--min-caption-width 100` (down to 50 is fine; `find_captions`
   already requires a leading "Figure"/"Fig."/"Table" and rejects inline
   cross-references) and use the same value for `build_manifest.py`. Zero
   captions at all makes the script print the threshold that would work.

3. **Build the manifest** from the repo root. `--out-dir` and
   `--source-pdf-repo-path` are written verbatim into the manifest, so use the
   bucket the topic *currently* sits in (see repo `CLAUDE.md`).
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/build_manifest.py \
     --pdf in-progress/<Topic>/<paper>.pdf \
     --out-dir in-progress/<Topic>/assets \
     --source-pdf-repo-path in-progress/<Topic>/<paper>.pdf
   ```
   It finds captions (a block that starts with "Figure N"/"Table N" and isn't
   an inline cross-reference; on a number collision it prefers a block with a
   separator `: . | — –` after the number, then a capitalized next word, then
   length), measures the document layout once, picks each visual's top edge
   (a floor of preceding captions and body text, then a walk up through the
   visual's own ink to the first real whitespace gap) and horizontal bounds
   (the union of clip-corrected ink and text in its band, widened by the
   caption), renders at 3x zoom, tries `pdfplumber` for table markdown (kept
   only if rows/columns are consistent with no empty cells, otherwise
   `parser_confidence: low`), finds a `nearby_text` snippet, and flags bad
   crops in a `SUSPECT CROPS` block on stderr (degenerate region, or a figure
   crop that is mostly body prose), forcing them to `low`. It writes
   `image-manifest.json` (schema: `references/image-manifest-schema.md`) and
   runs the quality checks.

4. **Fix flagged or suspicious crops** (see the symptom index), rebuilding
   with the override flags: `--crop-top-override`, `--crop-bottom-override`,
   `--crop-left-override`, `--crop-right-override`, all `"page:kind:num=value"`
   comma-separated, e.g. `"8:table:3=255,12:figure:3=60"`. Read the values off
   `dump_blocks.py <pdf> <page> [<page>...]`, which prints every text block's
   bbox and text top to bottom. Rebuild once with all overrides together.

5. **Visual check** when any blind spot above applies (usually it does).

6. **Verify** (also after any hand edit of the manifest):
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/verify_manifest.py \
     in-progress/<Topic>/assets/image-manifest.json .
   ```
   It confirms every `file` exists and is non-empty, there are no duplicate
   ids/paths/contents, and every entry has the required keys.

## Visual check

```bash
uv run python .claude/skills/pdf-figure-table-parser/scripts/make_review_thumbs.py \
  in-progress/<Topic>/assets/image-manifest.json <scratchpad>/thumbs
```
This writes `<id>.jpg` downscaled to 900px and prints id, original size and
caption per image. Don't open them yourself. Spawn one subagent, give it the
folder, and tell it, per image: the expected content (from the caption), to
read only the thumbnails, and to **report only problems as text** (clipped
edge, neighbouring prose or another visual included, large blank margin, a
missing legend or panel row), quoting the visible title or column headers of
anything it flags. It can mislabel images, so cross-check a flagged one
against its caption and pixel size, or ask the subagent to re-read just that
file, before changing anything. Then fix with the override flags and rebuild.

## Symptom index

| What you're seeing | Section |
|---|---|
| Fewer captions than the paper has | Workflow step 2 (gap warning), "Two-column papers" |
| Crop a few pixels tall (`SUSPECT CROPS`: degenerate) | "Sub-captions or table rows sit flush left", or "Caption above its content" |
| Crop swallowed the paragraph above the figure | "Figures that float mid-page" |
| Crop is mostly blank margin, figure shrunk in the middle | "Clipped ink" |
| Figure renders but is missing its lower half | "A caption in the middle of a multi-panel figure" |
| Outer table columns cut off, or a short-caption crop too narrow | "Single-column paper misclassified" and "Ruleless tables" (visual check) |
| Crop landed on a neighbouring visual's content | "Caption above its content" (visual check) |
| `table_markdown` missing, table `low` | "Low-confidence tables" (usually fine) |

## Failure modes

### Clipped ink

`page.get_drawings()` reports bboxes *before* clipping, so a figure embedding
a cropped screenshot has paths like `x=(-310, 681)` on a 612pt page that show
nothing. Taking min/max over them stretches the crop to the full page.
`visible_drawing_rects` replays the clip stack from
`get_drawings(extended=True)` and intersects each path with its clip. Placed
rasters carry no clip info, so `visual_ink_rects` drops any image whose bbox
isn't fully inside the page (a clipped backdrop) and gates the rest on the
content area widened by 4% of the page width. `inspect_pdf.py` prints the raw
and visible drawing counts per page; a large gap means the paper clips
heavily. For a paper that genuinely runs figures into its margins, use
`--margin-x`.

### Caption above its content

The default bottom edge is 3pt above the caption, correct when the caption
sits *below* the visual. For the academic-table convention of captioning
*above*, the content sits below the caption, so the default crops the page
header or whitespace. Fix with **both** `--crop-top-override` (just below the
caption) and `--crop-bottom-override` (just below the last row), e.g.
`--crop-top-override "5:table:1=326" --crop-bottom-override "5:table:1=442"`.

This is a whole-paper style choice: once one table is caption-above, expect
every table in that paper to be, and check them all against `dump_blocks.py`
rather than fixing only the flagged ones. The sharpest form: a walk that
overshoots past a table's caption into the *neighbouring table's* cells
renders a plausible size, passes every check, and can even get
`parser_confidence: high` from `pdfplumber`. Confirm each final y-range doesn't
dip into the block above its own caption.

### Sub-captions or table rows sit flush left

`flush_left_blocks` identifies body prose by a block starting exactly on a
column edge. Two things look like that but aren't prose, and both anchor the
top floor just above the real caption, leaving a few points of height:
- a multi-panel figure's `(a) ...`/`(b) ...` sub-captions (one paper hit
  this on 5 of 13 figures, so check every multi-panel figure);
- **a table's own rows**, when its caption sits below it and the rows start
  on the column edge (9 of 19 visuals in one two-column paper).

Fix with `--crop-top-override` **alone**, set above the visual's real top
(the first panel or header row, via `dump_blocks.py`). The bottom edge is
already right. To tell this apart from caption-above: if the real content sits
*below* the caption, it's caption-above; if the blocks right above the caption
are sub-captions or table rows with the visual's own text above them, it's
this case.

### Figures that float mid-page

Body-column text is identified by its left edge (`column_left_edges`);
a figure's own text (panel labels, axis labels, callouts) is centered or
indented at least a couple of points off it. Widening `flush_left_blocks`'
`tol` past ~2pt classifies figure text as body text and crops figures to
nothing; fix a page with an override instead. The upward ink walk crosses gaps
up to 36pt (`max_gap`), so a genuinely larger internal gap loses a figure's top
rows, and a caption less than that from the text flow can pull in a line of it.
Both are override cases. Inline icons in running text are why the walk starts
at the lowest ink above the caption and why the floor exists.

### A caption in the middle of a multi-panel figure

If the caption sits between two panel rows (say bar charts, caption, then a
legend and a second row), the auto crop stops cleanly at the caption, renders
a normal size, and misses the second half; the next caption on the page then
gets a top edge inside that missing half. The tell in `dump_blocks.py`: body
text resumes only well after the *next* caption, with figure-internal blocks
in between. Fix both: `--crop-bottom-override` on the first figure and
`--crop-top-override` on the second, starting where the first now ends.

### Two-column papers

Two-column layouts mix full-width and single-column floats. Single-column
captions are the ones `--min-caption-width` filters (workflow step 2).
`auto_crop_hbounds` reads each visual's own clip-corrected ink, so a
full-width table no longer comes out one column wide; comparing pixel widths
across visuals (they should cluster at "one column" and "full width", not a
continuum) is a fast text-only way to spot an outlier. `--margin-x` remains as
a manual override.

**A caption narrower than its figure.** A short centered caption (e.g. 200pt
under a figure of two side-by-side 240pt panels) is classified into one column
and clips the figure to its width. This is invisible to every automated check;
catch it by comparing pixel width to the raster rects `inspect_pdf.py`
prints, then fix with `--crop-left-override`/`--crop-right-override` set to the
outer edges of those rects.

### Single-column paper misclassified as two-column

`caption_column` once classified a caption from its own width alone, so a
short centered caption in a single-column paper looked like it lived in a
non-existent half-page column and the table's wider cells were cut off.
`build_manifest.py` now computes `is_two_column_doc(...)` once (a real second
column starts past ~25% of the page width from the first, unlike the ~15-20pt
indent of nested lists) and passes `two_column=...` through; when false,
`caption_column` always returns `"full"`. `inspect_pdf.py` prints which way
this went next to the column edges. Check it on any paper with a short,
narrow-captioned table.

### Ruleless tables

A table with no drawn rules has no vector ink and no images, so its width
used to fall back to the caption's bbox, which clips outer columns when the
caption is shorter than the table. `auto_crop_hbounds` now also unions in
text-block rects found in the final `[top, bottom]` band. The mirror failure
(too *wide*) happens when a neighbour's ink or a body-width sub-caption falls
inside the band. Either direction is a one-line fix with
`--crop-left-override`/`--crop-right-override` (per entry; every other visual
keeps its auto bounds). Get the x value from `dump_blocks.py` bboxes or a
one-off `visual_ink_rects(page)` call.

### Low-confidence tables

Many academic tables have no ruling lines, so `pdfplumber`'s line-based
detection finds nothing or something fragmented. That is expected, not worth
fighting: the schema prefers an honest `parser_confidence: low` image-only
entry over a silently mangled cell. To push on a specific table by hand,
lower `pdfplumber`'s word-clustering `x_tolerance` (e.g. 1.5 instead of 3) to
split glued words like "Strongoptimizer"; this inspects text, not images, so
it's fine.

## Files

```
pdf-figure-table-parser/
├── SKILL.md
├── references/image-manifest-schema.md   field-by-field schema docs
└── scripts/
    ├── pdf_parser_lib.py                 shared logic
    ├── inspect_pdf.py                    dry-run: captions, numbering gaps, image/drawing counts
    ├── dump_blocks.py                    per-page text block dump (for override values)
    ├── build_manifest.py                 main driver: extract + write manifest
    ├── verify_manifest.py                standalone quality check
    └── make_review_thumbs.py             downscaled copies for the subagent visual check
```
