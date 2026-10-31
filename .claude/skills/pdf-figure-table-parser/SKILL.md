---
name: pdf-figure-table-parser
description: Use this skill whenever you need to extract figures, tables, or diagrams out of a PDF (especially an academic/arXiv paper) into image files plus a structured manifest, for a downstream step (a writer/summarizer agent, a blog pipeline, a report) that must never load the actual image bytes into its own context. Trigger this whenever the user mentions parsing a paper's PDF for figures/tables, building an image-manifest, or references tools like docling/marker/nougat for PDF visual extraction -- this skill's PyMuPDF-based approach works even when huggingface.co-hosted model downloads are blocked by network/egress policy (a common failure mode for docling and similar ML-model-backed parsers in sandboxed environments), and produces reliable, inspectable crops for born-digital PDFs without any OCR or vision model at all.
---

# PDF Figure/Table Parser (Step 1 in this repo's pipeline)

Step 1 runs *before* `blog-writer` (Step 2), because the Writer may only
reference figures that were extracted. The skill itself has no dependency on
that pipeline.

## Why PyMuPDF and no ML parser

`docling`/`marker`/`nougat` download models from `huggingface.co`, which is
usually blocked by an egress allowlist in sandboxed environments (a policy
denial; don't retry or hunt for a mirror). A **born-digital PDF** (essentially
every arXiv paper) doesn't need them: PyMuPDF gives exact text positions,
embedded rasters and page rendering. These scripts find every
"Figure N"/"Table N" caption and render just that visual's region to PNG. No
model weights, no network, no OCR. A scanned PDF (empty or garbled
`page.get_text()`, near-zero drawings in `inspect_pdf.py`) needs OCR; this
skill doesn't apply.

## Images stay out of the main context

Judge crops with **text signals** (bounding boxes, caption strings, pixel
sizes, the build log, `SUSPECT CROPS`, `verify_manifest.py`) and fix problems
with the override flags, not by looking. When text can't settle it, do a
visual check through a subagent (see "Visual check"). Never open a full-size
PNG or a rendered PDF page in the main session.

Blind spots that no automated check catches:
- a crop horizontally too narrow or too wide (outer table columns clipped, a
  neighbour's ink bled in), especially for **short, centered table captions**,
  **side-by-side tables in a single-column paper**, and any manual left/right
  override;
- a crop that landed on a neighbouring visual's content;
- a multi-panel figure missing its second half;
- an **auto caption-above** table crop whose walk stopped in the wrong place
  (read the `stopped at ...` reason in the build log first).

## Workflow

1. **Set up once.** `uv sync` from the repo root. Run every script as
   `uv run python .claude/skills/pdf-figure-table-parser/scripts/<name>.py ...`
   from the repo root.

2. **Dry-run.**
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/inspect_pdf.py in-progress/<Topic>/<paper>.pdf
   ```
   Check the page count, content area, column edges and detected captions.
   **`WARNING: caption numbering has gaps`** means captions were filtered out,
   nearly always by `--min-caption-width` (default 400): a single-column
   caption in a two-column paper is only ~200-230pt wide. Re-run with e.g.
   `--min-caption-width 100` (down to 50 is fine) and use the same value for
   `build_manifest.py`.

3. **Build the manifest** from the repo root. `--out-dir` and
   `--source-pdf-repo-path` are written verbatim into the manifest, so use the
   bucket the topic *currently* sits in (repo `CLAUDE.md`).
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/build_manifest.py \
     --pdf in-progress/<Topic>/<paper>.pdf \
     --out-dir in-progress/<Topic>/assets \
     --source-pdf-repo-path in-progress/<Topic>/<paper>.pdf
   ```
   Per visual it picks a top edge (a floor of preceding captions and body
   text, then a walk up through the visual's own ink), horizontal bounds (the
   union of clip-corrected ink and text in its band, widened by the caption),
   renders at 3x zoom, tries `pdfplumber` for `table_markdown` (kept only when
   clean, otherwise `parser_confidence: low`), and finds a `nearby_text`
   snippet. Tables captioned above their content are detected and cropped
   downward automatically ("Caption above its content"). Every line of the
   log names how each edge was chosen. Bad crops land in a `SUSPECT CROPS`
   block on stderr and are forced to `low`.

4. **Fix flagged or suspicious crops** (symptom index below) with
   `--crop-top-override`, `--crop-bottom-override`, `--crop-left-override`,
   `--crop-right-override`, all `"page:kind:num=value"` comma-separated, e.g.
   `"8:table:3=255,12:figure:3=60"`. Read values off
   `dump_blocks.py <pdf> <page> [<page>...]` (every text block's bbox, top to
   bottom). Rebuild once with all overrides together; the edge checks re-run
   on manual values too.

5. **Visual check** when any blind spot above applies (usually it does).

6. **Verify** (also after any hand edit of the manifest):
   ```bash
   uv run python .claude/skills/pdf-figure-table-parser/scripts/verify_manifest.py \
     in-progress/<Topic>/assets/image-manifest.json .
   ```

## Visual check

```bash
uv run python .claude/skills/pdf-figure-table-parser/scripts/make_review_thumbs.py \
  in-progress/<Topic>/assets/image-manifest.json <scratchpad>/thumbs
```
This writes `<id>.jpg` downscaled to 900px and prints id, size and caption.
Don't open them yourself. Give one subagent the folder and, per image, the
expected content (from the caption); tell it to read only the thumbnails and
**report only problems as text** (clipped edge, neighbouring prose or another
visual included, large blank margin, a missing legend or panel row), quoting
the visible title or column headers of anything it flags. It can mislabel
images, so cross-check a flag against the caption, pixel size and
`dump_blocks.py` before changing anything. "No closing rule under the last
row" is often just a table without one; check for ink below with
`visual_ink_rects` before loosening an edge.

## Symptom index

| What you're seeing | Section |
|---|---|
| Fewer captions than the paper has | Workflow step 2 (gap warning), "Two-column papers" |
| Crop a few points tall (`degenerate`) | "Sub-captions or table rows sit flush left"; for a table, "Caption above its content" |
| `crop ... edge cuts through text block` / `ink ... sits just below/above` | "Edges that cut content" |
| Crop swallowed the paragraph above the figure | "Figures that float mid-page" |
| Crop mostly blank margin, figure shrunk in the middle | "Clipped ink" |
| Figure missing its lower half | "A caption in the middle of a multi-panel figure" |
| Outer table columns cut off, or too wide | "Two-column papers", "Ruleless tables" (visual check) |
| `table_markdown` missing, table `low` | "Low-confidence tables" (usually fine) |

## Failure modes

### Caption above its content

Most academic tables are captioned above. When at least half of the tables
without an override get a degenerate caption-below region, the whole paper is
treated as caption-above, and the log prints `Tables are captioned above their
content`. Each table is then cropped by `caption_above_crop`: a walk down from
the caption that stops at the next caption, at body text resuming (a block on
a body column edge that reads as prose or a numbered heading), at a gap over
40pt, or at the content area's bottom. The log line says
`auto caption-above, stopped at <reason>`. Two guards cover exceptions:

- A table that is still captioned below in such a paper keeps its usual
  region when that region holds the rules and the area under the caption
  doesn't, or when only one line of text sits under the caption.
- When the walk ends at a *figure* caption, that figure's panels sit between
  the table and its caption, so the region is cut at its widest whitespace
  gap.

`--tables-caption-above yes|no` forces the convention. A manual top or bottom
override for an entry always wins.

Check the `stopped at` reason against `dump_blocks.py`. Failures seen across
37 papers: a text-heavy table whose rows start on the margin and read as prose
(crop stops after a row or two), a table with no gap before the next figure or
the page bottom (crop too tall), and two tables side by side in one
single-column paper (each crop spans both; fix with left/right overrides). For
a manual fix, set **both** `--crop-top-override` (just below the caption) and
`--crop-bottom-override` (just below the last row).

### Edges that cut content

`crop_warnings` flags an edge that runs through a text block (at least 25% of
the block on each side; text wrapped beside the visual is ignored) and ink
within 3pt outside an edge (a cut table rule or axis; ink in the caption's own
band is ignored). This is how a too-tight manual override shows up. Move the
named edge past the block or ink the warning quotes.

### Sub-captions or table rows sit flush left

`flush_left_blocks` treats a block that starts exactly on a column edge as
body text. A multi-panel figure's `(a) ...`/`(b) ...` sub-captions, or a
caption-below table's own rows, can look like that, which floors the top edge
just above the caption and leaves a few points of height. Fix with
`--crop-top-override` **alone**, set above the visual's real top. If the real
content sits *below* the caption instead, it's the caption-above case.

### Figures that float mid-page

A figure's own text is centered or indented a couple of points off the
column edge, which is how it's told apart from body text. Don't widen
`flush_left_blocks`' `tol` past ~2pt; it classifies figure text as body text.
The upward ink walk crosses gaps up to 36pt, so a larger internal gap loses a
figure's top rows, and a caption less than that from the text flow can pull in
a line of it. Both are override cases.

### Clipped ink

`page.get_drawings()` reports bboxes *before* clipping (`x=(-310, 681)` on a
612pt page is normal for an embedded screenshot). `visible_drawing_rects`
replays the clip stack; `visual_ink_rects` drops rasters not fully on the page
and gates the rest on the content area widened by 4% of the page width.
`inspect_pdf.py` prints raw vs visible drawing counts; a large gap means heavy
clipping. For a paper whose figures really run into the margins, use
`--margin-x`.

### A caption in the middle of a multi-panel figure

If the caption sits between two panel rows, the crop stops at the caption and
misses the second half, and the next caption's crop starts inside that half.
The tell in `dump_blocks.py`: body text resumes only after the *next* caption.
Fix with `--crop-bottom-override` on the first figure and `--crop-top-override`
on the second.

### Two-column papers

Two-column layouts mix full-width and single-column floats; single-column
captions are the ones `--min-caption-width` filters. Pixel widths should
cluster at "one column" and "full width"; an outlier is worth a look. A short
centered caption under a figure wider than one column gets clipped to one
column: compare the pixel width to the raster rects `inspect_pdf.py` prints
and fix with left/right overrides. `is_two_column_doc` decides the layout once
per paper (`inspect_pdf.py` prints which way it went); a single-column paper
always uses full-width bounds.

### Ruleless tables

A table with no drawn rules has no ink, so its width comes from the text
blocks in its band. Too narrow or too wide (a neighbour's ink or a wide
sub-caption in the band) is a one-line fix with
`--crop-left-override`/`--crop-right-override`.

### Low-confidence tables

Many academic tables have no ruling lines, so `pdfplumber` finds nothing
usable. That's expected: an honest `parser_confidence: low` image-only entry
beats a mangled cell. To push on one table by hand, lower `pdfplumber`'s
`x_tolerance` (e.g. 1.5) to split glued words.

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
