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
     wins when there's a collision).
   - Estimates the top boundary of each visual's region (`auto_crop_top`):
     the bottom edge of the nearest preceding "paragraph-like" block on the
     same page (full-width prose, or another visual's own caption -- both
     work as a lower bound), falling back to a fixed top-of-page margin when
     nothing qualifies (typical for a figure sitting at the very top of a
     page, right after a page break).
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

## When the automatic crop boundary gets a page wrong

The heuristic in step 3 assumes a fairly standard single/double-column
academic layout. It can misjudge unusual pages: a figure that floats
mid-column with body text both above and below it, a caption placed *above*
its visual instead of below, or a two-column layout where the "paragraph
width" estimate doesn't match a particular section. When a rendered image's
pixel dimensions look implausible (e.g. absurdly short/tall, or you notice
two visuals' regions must have overlapped because their combined heights
exceed the page), don't open the PNG to check -- instead:

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

## Why tables often end up low-confidence, and why that's fine

Many academic tables have no ruling lines at all (just whitespace/alignment)
-- `pdfplumber`'s line-based table detection needs actual drawn lines to
find column/row boundaries, so it often finds nothing or something
fragmented on these. This isn't a bug in the script, and it isn't worth
fighting hard: the parser spec this manifest schema comes from explicitly
prefers an honest `parser_confidence: low` + image-only entry over a
structured table that silently mangled a cell (merged headers, misaligned
columns). `build_manifest.py` already applies this policy automatically.

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
