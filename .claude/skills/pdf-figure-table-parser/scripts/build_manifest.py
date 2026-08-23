#!/usr/bin/env python3
"""
Extract every figure/table/diagram out of a born-digital PDF and write a
normalized image-manifest.json (see ../references/image-manifest-schema.md
for the exact field semantics). This never opens or displays the rendered
PNGs -- only file sizes, pixel dimensions and text are inspected to build
and verify the manifest.

Run this from the repo root. --out-dir and --source-pdf-repo-path should
both be repo-relative paths: they end up verbatim in the manifest's "file"
and "source_pdf" fields, and quality checks resolve them against the
current working directory.

Usage:
    python build_manifest.py --pdf in-progress/RecursiveMAS/paper.pdf \\
        --out-dir in-progress/RecursiveMAS/assets \\
        --source-pdf-repo-path in-progress/RecursiveMAS/paper.pdf

    (Paths include the topic's bucket -- in-progress/, done/unpublished/ or
    done/published/ -- because they are baked into the manifest verbatim.
    See the repo CLAUDE.md's topic-directory section.)

Optional:
    --crop-top-override page:kind:num=y[,page:kind:num=y...]
        Manually override the auto-detected top boundary for specific
        visuals, e.g. "8:table:3=255". Use dump_blocks.py to find the right
        y value when the automatic heuristic gets a page wrong (unusual
        layouts, two-column papers, captions above rather than below the
        visual).
    --crop-bottom-override page:kind:num=y[,page:kind:num=y...]
        Manually override the bottom boundary (default: 3pt above the
        caption's own top edge, which assumes the caption sits below its
        visual). Needed for the common academic-table convention of
        captioning ABOVE the table: there the real content is below the
        caption, so both --crop-top-override (set to just below the
        caption) and --crop-bottom-override (set to just below the table's
        last row) are needed together. Use dump_blocks.py to find the y
        value just below the table's last row.
    --zoom FLOAT           Render zoom factor (default 3.0, ~216 DPI at
                            standard letter/A4 page size).
    --margin-x FLOAT       Force a fixed horizontal crop margin in points
                            from each page edge for every visual, overriding
                            the default per-visual drawing/image-based
                            bounds (see auto_crop_hbounds in pdf_parser_lib.py).
                            Not needed in normal use -- only as a manual
                            escape hatch if the automatic bounds are wrong
                            for a specific document.
    --min-caption-width FLOAT
                            Minimum caption block width to accept as a real
                            caption (default 400). Lower this for two-column
                            papers, where a caption sitting in a single
                            column can be ~220pt wide instead of spanning
                            the full page.
"""
import argparse
import os
import sys

import pymupdf
import pdf_parser_lib as lib

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


def parse_overrides(raw):
    overrides = {}
    if not raw:
        return overrides
    for item in raw.split(","):
        key, _, y = item.partition("=")
        page, kind, num = key.split(":")
        overrides[(int(page), kind, int(num))] = float(y)
    return overrides


def try_table_markdown(pdf_path, page_no, rect):
    """
    Attempt clean structured-table extraction via pdfplumber's default
    (ruled-line) strategy, restricted to the visual's own crop region. Many
    academic tables have no ruling lines at all, in which case this reliably
    returns nothing usable -- that's expected, not a bug, and the caller
    should fall back to the image with parser_confidence: low. Returns
    markdown string or None.
    """
    if pdfplumber is None:
        return None
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no - 1]
        crop = page.crop((rect.x0, rect.y0, rect.x1, rect.y1))
        table = crop.extract_table()
        if not table or len(table) < 2:
            return None
        width = len(table[0])
        if width < 2 or any(len(row) != width for row in table):
            return None
        if any(cell is None or cell.strip() == "" for row in table for cell in row):
            return None
        lines = []
        lines.append("| " + " | ".join(str(c).replace("\n", " ").strip() for c in table[0]) + " |")
        lines.append("| " + " | ".join(["---"] * width) + " |")
        for row in table[1:]:
            lines.append("| " + " | ".join(str(c).replace("\n", " ").strip() for c in row) + " |")
        return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True, help="Directory to receive images/ and image-manifest.json")
    ap.add_argument("--source-pdf-repo-path", required=True, help="Value for the manifest's source_pdf field")
    ap.add_argument("--crop-top-override", default="")
    ap.add_argument("--crop-bottom-override", default="")
    ap.add_argument("--zoom", type=float, default=3.0)
    ap.add_argument("--margin-x", type=float, default=None)
    ap.add_argument("--min-caption-width", type=float, default=400.0)
    args = ap.parse_args()

    doc = lib.open_doc(args.pdf)
    captions = lib.find_captions(doc, min_caption_width=args.min_caption_width)
    if not captions:
        print("No Figure/Table captions detected. Nothing to extract.", file=sys.stderr)
        sys.exit(1)

    all_blocks = lib.page_blocks(doc)
    caption_bboxes = {(c["page"], c["bbox"]) for c in captions}
    captions_by_page = {}
    for c in captions:
        captions_by_page.setdefault(c["page"], []).append(c)

    # Document-level layout, measured once: where the body text actually
    # lives, and which blocks are running prose. Both feed the crop
    # heuristics -- see content_area() in pdf_parser_lib.py for why a
    # page-edge constant is not good enough.
    prose = lib.prose_blocks(all_blocks)
    area = lib.content_area(all_blocks)
    top_margin = area.y0 - 4 if area is not None else 58.0
    if area is None:
        print("Note: too little body prose to measure a content area; "
              "falling back to page-edge margins.", file=sys.stderr)

    column_w = lib.estimate_column_width(all_blocks)
    prose_bboxes = {(b["page"], b["bbox"]) for b in prose}
    col_edges = lib.column_left_edges(all_blocks)
    barriers = lib.flush_left_blocks(all_blocks, col_edges, column_width=column_w)
    for b in barriers:
        b["is_prose"] = (b["page"], b["bbox"]) in prose_bboxes

    # Whole-document signal for caption_column/auto_crop_*: a real two-column
    # layout, not just the close-together edges a single-column paper's
    # nested-list indentation also produces (see is_two_column_doc). Without
    # this, a narrow single-column caption gets misclassified as living in a
    # "left"/"right" half-page column that doesn't actually exist, and its
    # own wider content past the artificial midpoint gets excluded from the
    # crop -- see auto_crop_hbounds' docstring.
    two_column = lib.is_two_column_doc(col_edges, doc[0].rect.width)

    overrides = parse_overrides(args.crop_top_override)
    bottom_overrides = parse_overrides(args.crop_bottom_override)

    images_dir = os.path.join(args.out_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    ink_by_page = {}
    text_by_page = {}
    manifest_images = []
    warned = []
    print(f"Detected {len(captions)} visual(s):\n")
    for i, c in enumerate(captions, start=1):
        page_no, kind, num = c["page"], c["kind"], c["num"]
        page = doc[page_no - 1]
        page_w = page.rect.width

        if page_no not in ink_by_page:
            ink_by_page[page_no] = lib.visual_ink_rects(page, area)
        ink = lib.rects_in_column(ink_by_page[page_no], c["bbox"], page_w, two_column=two_column)

        if page_no not in text_by_page:
            text_by_page[page_no] = [pymupdf.Rect(b["bbox"]) for b in all_blocks if b["page"] == page_no]
        text_rects = lib.rects_in_column(text_by_page[page_no], c["bbox"], page_w, two_column=two_column)

        key = (page_no, kind, num)
        if key in overrides:
            top = overrides[key]
            source = "manual override"
        else:
            top = lib.auto_crop_top(page_no, c["bbox"], captions_by_page, page_w,
                                    default_margin=top_margin, ink_rects=ink,
                                    barriers=barriers, text_blocks=all_blocks, kind=kind,
                                    two_column=two_column)
            source = "auto heuristic"

        bottom = bottom_overrides.get(key, c["bbox"][1] - 3)
        if args.margin_x is not None:
            left, right = args.margin_x, page_w - args.margin_x
            hsource = "explicit --margin-x"
        else:
            left, right = lib.auto_crop_hbounds(page, top, bottom, c["bbox"],
                                                ink_rects=ink, text_rects=text_rects,
                                                two_column=two_column)
            hsource = "clipped ink/caption"
        rect = pymupdf.Rect(left, top, right, bottom)
        if rect.height < 1 or rect.width < 1:
            # An empty region can't be rendered at all (pymupdf raises), and a
            # hard crash here would lose the other 16 good crops. Widen it to
            # something renderable; crop_warnings flags it below and the entry
            # lands as parser_confidence=low with a visible complaint.
            rect = pymupdf.Rect(rect.x0, rect.y0,
                                max(rect.x1, rect.x0 + 1), max(rect.y1, rect.y0 + 1))

        fname = f"picture-{i:03d}.png"
        fpath = os.path.join(images_dir, fname)
        w, h = lib.render_crop(page, rect, fpath, zoom=args.zoom)

        nearby = lib.find_nearby_text(all_blocks, caption_bboxes, c["label"])
        entry_type = "table" if kind == "table" else "figure"

        table_md = None
        confidence = "high"
        if entry_type == "table":
            table_md = try_table_markdown(args.pdf, page_no, rect)
            confidence = "high" if table_md else "low"

        problems = lib.crop_warnings(rect, page_no, prose, kind=kind)
        if problems:
            confidence = "low"
            warned.append((f"img-{i:03d}", page_no, c["label"], problems))

        entry = {
            "id": f"img-{i:03d}",
            "file": os.path.join(args.out_dir, "images", fname).replace(os.sep, "/"),
            "type": entry_type,
            "page": page_no,
            "caption": c["text"],
            "nearby_text": nearby,
            "parser_confidence": confidence,
        }
        if table_md:
            entry["table_markdown"] = table_md

        manifest_images.append(entry)
        print(f"  {entry['id']}: page {page_no} {kind} {num} -> {fname} "
              f"({w}x{h}px, crop-top={top:.1f} via {source}, hbounds via {hsource}, confidence={confidence})")

    manifest = {
        "source_pdf": args.source_pdf_repo_path,
        "generated_by": "pdf-figure-table-parser skill (pymupdf caption-anchored region render)",
        "images": manifest_images,
    }
    manifest_path = os.path.join(args.out_dir, "image-manifest.json")
    lib.save_json(manifest, manifest_path)
    print(f"\nWrote {manifest_path}")

    if warned:
        print(f"\nSUSPECT CROPS ({len(warned)}), marked parser_confidence=low:", file=sys.stderr)
        for eid, page_no, label, problems in warned:
            print(f" - {eid} (page {page_no}, {label}):", file=sys.stderr)
            for p in problems:
                print(f"     {p}", file=sys.stderr)
        print("   Inspect with dump_blocks.py and rerun with the appropriate "
              "--crop-top-override / --crop-bottom-override.", file=sys.stderr)

    # Manifest paths are repo-relative by convention (see module docstring),
    # so they resolve against the current working directory.
    errors = lib.verify_manifest(manifest, repo_root=os.getcwd())
    if errors:
        print("\nQUALITY CHECK FAILURES:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        sys.exit(1)
    print("Quality checks passed: all files exist, non-zero size, no duplicate ids/files/content.")


if __name__ == "__main__":
    main()
