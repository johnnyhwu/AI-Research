---
name: pdf-figure-table-parser
description: Use this skill whenever you need to extract figures, tables, or diagrams out of a PDF (especially an academic/arXiv paper) into image files plus a structured manifest, for a downstream step (a writer/summarizer agent, a blog pipeline, a report) that must never load the actual image bytes into its own context. Trigger this whenever the user mentions parsing a paper's PDF for figures/tables, building an image-manifest, or references tools like docling/marker/nougat for PDF visual extraction -- this skill's PyMuPDF-based approach works even when huggingface.co-hosted model downloads are blocked by network/egress policy (a common failure mode for docling and similar ML-model-backed parsers in sandboxed environments), and produces reliable, inspectable crops for born-digital PDFs without any OCR or vision model at all.
---

# PDF Figure/Table Parser

## Why this skill exists

The obvious way to parse a PDF's figures and tables is a tool like
`docling`, `marker`, or `nougat`. All three are good tools, but they lean on
downloaded deep-learning models (layout detection, table-structure
recognition, OCR) hosted on `huggingface.co`. In a sandboxed agent
environment with an egress allowlist, that host is very often blocked
(policy denial, not a bug) -- and there is no way around a network policy
denial, so don't spend time retrying it or hunting for a mirror.

For a **born-digital PDF** (the PDF was produced by LaTeX/Word/etc., not a
scan -- true for essentially every arXiv paper), you don't need any ML model
at all. **PyMuPDF** (`import pymupdf`, formerly `fitz`) gives you exact text
positions, embedded raster images, and high-fidelity page rendering, purely
from the PDF's own internal structure. This skill's scripts use that to
locate every "Figure N" / "Table N" caption in the document, and render just
that visual's region to a PNG, anchored precisely between the surrounding
text and the caption. No model weights, no network dependency, no OCR.

This only works for born-digital PDFs. If `page.get_text()` on a sample page
comes back empty or garbled, the PDF is a scan and you actually do need OCR
(the `pdf` skill's OCR section, or a docling/nougat setup where network
access to model hosts is actually available) -- check for that early with
`inspect_pdf.py` (a healthy page will show non-trivial vector drawing counts
and/or text captions; a scanned page will show essentially nothing).

## The hard rule: never load the images yourself

The entire point of doing this extraction step is so that a *later* agent
(a writer, a summarizer, a reviewer) never has to burn tokens or risk
misreading a cropped chart by loading image bytes into its context. That
discipline starts here: **never use an image-viewing tool on the PDF pages
or the PNGs you produce, at any point in this workflow, even to "double
check" a low-confidence extraction.** Every verification in this skill is
done with text: bounding boxes, caption strings, file sizes, pixel
dimensions, JSON schema checks. If something looks wrong, the fix is better
heuristics or a manual crop-boundary override (see below) -- not a peek.

If the user hasn't stated this rule explicitly, apply it anyway by default;
it's the reason a separate parsing step is worth having at all.

## Workflow

1. **Set up dependencies once per environment.**
   ```bash
   bash scripts/setup_env.sh
   source .venv-pdf-parser/bin/activate
   ```
   This installs `pymupdf`, `pdfplumber`, and `pillow` from PyPI -- no
   `huggingface.co` traffic, so it works under the same network policy that
   blocks docling.

2. **Dry-run the PDF first.**
   ```bash
   python scripts/inspect_pdf.py path/to/paper.pdf
   ```
   Read the printed page count, embedded-image counts, vector-drawing
   counts, and the list of detected captions with their page + bounding box.
   This is where you catch problems before spending effort: zero captions
   detected probably means the paper doesn't caption its visuals the usual
   way (check for "Fig." abbreviations, or non-English captions -- the
   caption regex in `pdf_parser_lib.py` is easy to extend); near-zero
   drawing/image counts on every page probably means it's a scanned PDF.

3. **Build the manifest.**
   ```bash
   python scripts/build_manifest.py \
     --pdf path/to/paper.pdf \
     --out-dir docs/<slug>/assets \
     --source-pdf-repo-path docs/<slug>/source.pdf
   ```
   Run this **from the repo root** -- `--out-dir` and
   `--source-pdf-repo-path` are repo-relative paths that get written
   verbatim into the manifest and checked against the current directory.

   This does all of the following automatically:
   - Finds every caption (`find_captions` in `pdf_parser_lib.py`). A caption
     is a block that *starts* with "Figure N"/"Table N" and isn't followed
     immediately by a comma (that comma pattern means it's an inline
     cross-reference like "Table 2, Figure 3, and Table 3 test the design
     choices...", not the real caption -- the real caption for the same
     number, found elsewhere, is always the longer match, so the longer one
     wins when there's a collision). A caption block also has to be at least
     `--min-caption-width` points wide (default 400) to be accepted, which
     filters out narrow incidental matches -- **but on a two-column paper, a
     caption that sits inside a single column can legitimately be only
     ~200-230pt wide.** If `inspect_pdf.py` finds suspiciously few captions
     for a paper you know has more figures/tables, check whether it's
     two-column (see below) and rerun with e.g. `--min-caption-width 150`.
   - Measures the document's own layout once (`content_area`,
     `column_left_edges`): the rectangle its body text prints inside, and the
     x-coordinate(s) its text columns start at. Everything below is expressed
     relative to these rather than to page-edge constants, so the heuristics
     travel across paper templates. `inspect_pdf.py` prints both -- if they
     look wrong, stop, because every crop will be wrong too.
   - Estimates the top boundary of each visual's region (`auto_crop_top`) in
     two stages: a *floor* nothing may cross (the content area's top edge, any
     preceding caption on the same page/column, and the lowest body-column
     text block above the caption), then a walk upward through the visual's
     own ink from the lowest ink above the caption, stopping at the first real
     whitespace gap. The floor is what keeps a mid-page figure from
     swallowing the paragraph above it; the walk is what removes the blank
     band between the floor and the figure.
   - Derives the left/right bounds of each visual's region (`auto_crop_hbounds`):
     the union of every ink rect fully contained in the visual's vertical
     band, widened by the caption's own bbox as a floor. This reads the PDF's
     own drawing commands as ground truth for where a figure's or table's ink
     actually is, rather than guessing from a single page-wide column-width
     estimate -- see below for why that guess reliably breaks on two-column
     papers. Pass `--margin-x` to force a fixed page-edge margin instead (an
     explicit escape hatch, not needed in normal use).
   - Renders each region to `picture-NNN.png` at 3x zoom (~216 DPI) via
     `page.get_pixmap(clip=...)`.
   - Attempts clean structured-table extraction via `pdfplumber` for table
     visuals, and includes it as `table_markdown` only if the result has
     consistent row/column counts and no empty cells -- otherwise the image
     is the source of truth and the entry is marked `parser_confidence: low`
     (see below on why this often fails, and what "good enough" looks like).
   - Finds a `nearby_text` snippet: the first place elsewhere in the
     document body that mentions the same "Figure N"/"Table N", useful for
     a downstream step trying to understand why the visual matters.
   - Sanity-checks every crop rectangle against the page's text
     (`crop_warnings`) and prints a `SUSPECT CROPS` block to stderr for any
     that fail, forcing those entries to `parser_confidence: "low"`. Two
     things get flagged: a degenerate (near-empty) region, which almost
     always means the caption sits *above* its visual, and a figure crop
     whose height is mostly body prose, which means the top boundary
     overshot. Read that block -- it is the cheap, image-free signal that a
     crop needs a manual override, and it exists precisely so a wrong crop
     can't ship looking confident.
   - Writes `image-manifest.json` matching the schema in
     `references/image-manifest-schema.md`, and runs the quality checks
     (step 4) automatically before exiting.

4. **Quality-check independently, any time.**
   ```bash
   python scripts/verify_manifest.py docs/<slug>/assets/image-manifest.json
   ```
   Confirms every `file` path exists and is non-zero size, no duplicate
   `id`s or file paths (including duplicate *content*, via checksum), and
   every entry has the required keys. Run this again after any manual edit
   to the manifest (e.g. a downstream agent filling in a `table_markdown`
   by hand).

## Clipped ink: why raw drawing bboxes can't be trusted

`page.get_drawings()` reports each path's bbox *before* the clipping path is
applied, and modern papers clip constantly -- any figure that embeds a
screenshot or a cropped photo typically places the full raster far outside
the page and shows a window onto it. Bboxes like `x=(-310, 681)` on a 612pt
page are completely normal, and none of that ink is visible.

Taking `min`/`max` over those bboxes, as `auto_crop_hbounds` originally did,
stretches a figure's crop to the full page width: the render is mostly blank
margin with the actual figure shrunk in the middle. `visible_drawing_rects`
fixes this by replaying the clip stack from `page.get_drawings(extended=True)`
(which additionally emits `clip`/`group` entries with a scissor rect and a
nesting `level`) and intersecting each path with the clip actually in force.

Placed **raster images** get no clip information from PyMuPDF at all, so
`visual_ink_rects` handles them separately: an image whose bbox is not fully
inside the page is dropped outright (it is a clipped backdrop, and its bbox
describes the source, not what shows), and the rest are gated on the
document's `content_area` widened by 4% of the page width. That tolerance
lets a figure bleed a little into the margin while rejecting a raster that
claims the whole margin. A document that genuinely runs figures deep into its
margins is the case to reach for `--margin-x` on.

`inspect_pdf.py` prints both counts per page ("N vector drawing item(s), M of
them visible after clipping"). A large gap between the two means this paper
clips heavily, and the crops depend on the clip-stack logic being right.

## When the automatic crop boundary gets a page wrong

The heuristic in step 3 assumes a fairly standard single/double-column
academic layout. It can still misjudge unusual pages -- most often a caption
placed *above* its visual instead of below. `build_manifest.py`'s
`SUSPECT CROPS` block flags the cases it can detect; a crop can also be
subtly wrong without tripping it. When a rendered image's pixel dimensions
look implausible (e.g. absurdly short/tall, or you notice two visuals'
regions must have overlapped because their combined heights exceed the page),
don't open the PNG to check -- instead:

```bash
python scripts/dump_blocks.py path/to/paper.pdf <page_num>
```

This prints every text block's bounding box and text on that page, sorted
top to bottom -- purely textual, so it doesn't break the "never look at the
image" rule. Use it to read off the right y-coordinate by eye (the value
just below the last real paragraph and just above the caption), then rerun
`build_manifest.py` with:

```bash
--crop-top-override "8:table:3=255,12:figure:3=60"
```

(format: `page:kind:num=y`, comma-separated for multiple overrides).

**Caption-above-content is a separate case from a merely-wrong top boundary,
and needs both overrides together.** `build_manifest.py`'s default bottom
boundary is always "3pt above the caption's own top edge" -- correct for the
usual figure convention (caption below the visual), but backwards for the
common academic-table convention of captioning *above* the table. On a page
like that, the real table content sits *below* the caption, so leaving the
default bottom boundary in place crops the page header or blank space above
the caption instead of the table -- `--crop-top-override` alone can't fix
this, since it only moves the top edge and the bottom edge is still anchored
above the caption. Use `dump_blocks.py` to find the y-coordinate just below
the table's last row, and pass it via `--crop-bottom-override` (same
`page:kind:num=y` format) alongside a `--crop-top-override` set to just below
the caption:

```bash
--crop-top-override "5:table:1=326" --crop-bottom-override "5:table:1=442"
```

This convention (caption above, content below) is common enough for tables
specifically that it's worth checking every table entry's rendered
dimensions against `dump_blocks.py` output up front on any paper with
ruleless/dense tables, rather than waiting for a visibly-wrong pixel size to
notice it -- a crop that grabs the page's running header text instead of the
table can still produce a plausible-looking, non-degenerate pixel size.

### Figures that float mid-page

A figure with body text above it and its caption below it used to be the
worst case here: the top boundary anchored only on other *captions*, so with
none above it on the page the crop started at the top-of-page margin and
swallowed every heading and paragraph between there and the figure. This is
now handled automatically -- `auto_crop_top`'s floor includes body-column
text, and the ink walk closes the remaining gap -- but the mechanism is worth
knowing, because it rests on one specific signal:

**Body-column text is identified by its left edge, not by how it reads.** A
paragraph or a section heading starts exactly on a column edge
(`column_left_edges`); a figure's own internal text -- panel labels, axis
labels, callouts, quoted model output -- is centred or indented inside the
figure and lands at least a couple of points off it. `flush_left_blocks`
splits them on that, plus a minimum width so a stray `(a)` at the far left of
a figure isn't mistaken for a paragraph.

Two consequences to keep in mind when a page still comes out wrong:

- Widening `flush_left_blocks`' `tol` past ~2pt starts classifying
  figure-internal text as body text, which crops figures to nothing. Fix the
  page with `--crop-top-override` instead.
- The ink walk crosses gaps up to `auto_crop_top`'s `max_gap` (36pt), which
  covers the whitespace between stacked panel rows in a multi-row figure. A
  figure with a genuinely larger internal gap loses its top rows; one whose
  caption is separated from the page's text flow by less than that can pull
  in a line of it. Both are override cases, not tuning cases.

Papers that drop inline icons into running text (a model logo mid-sentence,
say) are the reason the walk starts at the *lowest ink above the caption*
rather than at the caption, and the reason the floor exists at all: those
icons are real ink sitting inside body paragraphs and headings, and without
a floor the walk would happily chain up through them.

## Two-column papers: what to watch for

A two-column academic layout (very common for conference-style papers, less
so for arXiv preprints in general but not rare) routinely mixes
**full-width** floats (a wide table spanning both columns) with
**single-column** floats (a figure or table confined to one column) on the
same document. Two symptoms show up together and both trace back to the
same root cause -- a single-column-width assumption baked into a heuristic:

- `inspect_pdf.py` finds fewer captions than the paper actually has ->
  the missing ones are single-column-width captions getting filtered by
  `--min-caption-width`'s default of 400. Fix: rerun `inspect_pdf.py`/
  `build_manifest.py` with a lower value (e.g. `150`) once you confirm
  (`dump_blocks.py`) that the "missing" captions really are narrower,
  single-column blocks and not noise.
- A full-width table renders cropped to roughly one column's width, with
  the other half cut off -> this was `auto_crop_hbounds`'s predecessor bug:
  it derived one page-wide margin from the *median* body-text column width,
  which is representative of the many single-column paragraphs but wrong
  for the few floats that span both columns. `auto_crop_hbounds` now reads
  each visual's own clip-corrected ink instead (see "Clipped ink" above), so
  this shouldn't recur -- but if you ever see it, or the opposite symptom of
  a figure marooned in blank margin, `--margin-x` is still there as a manual override,
  and comparing pixel widths across all extracted visuals (they should
  cluster into one or two consistent widths -- "one column" and "full
  width" -- not a continuum) is a fast, image-free way to spot which entries
  are off.

The same low-`--min-caption-width` fix applies beyond two-column layouts,
too: some single-column papers use a narrower-than-usual text column (e.g.
~345pt instead of the ~400-480pt a US-letter/A4 page with normal margins
usually gives you), and a small inset figure's caption can be narrower still
if it sits beside other content rather than spanning the full column. If
`inspect_pdf.py` finds zero or suspiciously few captions on a paper that
isn't two-column, don't assume two-column-ness is the only possible cause --
check the actual caption block widths with `dump_blocks.py` and lower
`--min-caption-width` to whatever the real minimum is (down to a very low
value like `50` is fine; the risk of noise from *other* short blocks
matching the regex is low, since `find_captions` already requires the block
to start with "Figure"/"Fig."/"Table" and reject inline cross-references).

## Why tables often end up low-confidence, and why that's fine

Many academic tables have no ruling lines at all (just whitespace/alignment)
-- `pdfplumber`'s line-based table detection needs actual drawn lines to
find column/row boundaries, so it often finds nothing or something
fragmented on these. This isn't a bug in the script, and it isn't worth
fighting hard: this repo's manifest schema explicitly prefers an honest
`parser_confidence: low` + image-only entry over a structured table that
silently mangled a cell (merged headers, misaligned columns).
`build_manifest.py` already applies this policy automatically.

If you want to push further on a specific ruleless table by hand: lowering
`pdfplumber`'s word-clustering `x_tolerance` (e.g. `page.extract_words(x_tolerance=1.5)`
instead of the default 3) can fix words getting glued together
(`"Strongoptimizer"` -> `"Strong"`, `"optimizer"`) on fonts with tight
letter-spacing. This isn't wired into `build_manifest.py` because tuning it
safely in general (without breaking cases where merging is correct) needs a
human or agent to eyeball the *text* output per-document -- which is fine to
do, since that's text, not image, inspection.

## Files in this skill

```
pdf-figure-table-parser/
├── SKILL.md                              (this file)
├── references/
│   └── image-manifest-schema.md          field-by-field schema docs
└── scripts/
    ├── requirements.txt                  pymupdf, pdfplumber, pillow
    ├── setup_env.sh                      one-shot venv bootstrap
    ├── pdf_parser_lib.py                 shared logic, imported by the rest
    ├── inspect_pdf.py                    dry-run: captions + image/drawing counts
    ├── dump_blocks.py                    manual debugging: per-page text block dump
    ├── build_manifest.py                 main driver: extract + write manifest
    └── verify_manifest.py                standalone quality-check
```
