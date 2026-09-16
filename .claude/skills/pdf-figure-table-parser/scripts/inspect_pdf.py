#!/usr/bin/env python3
"""
Dry-run a PDF before extracting anything: page count, embedded raster image
counts, vector-drawing counts per page, and every Figure/Table caption it can
detect (with page + bounding box). Read this output as TEXT -- do not open
the PDF or any rendered image in an image viewer / Read tool to "double
check"; that defeats the whole point of this pipeline.

Usage:
    python inspect_pdf.py <pdf_path> [--min-caption-width N]

    --min-caption-width defaults to 400, same as build_manifest.py. Lower it
    (e.g. 150) to also see narrow single-column captions before deciding
    what to pass to build_manifest.py -- see SKILL.md's two-column-papers
    section for when this matters.
"""
import sys
import pdf_parser_lib as lib


def main():
    args = sys.argv[1:]
    min_caption_width = 400.0
    if "--min-caption-width" in args:
        i = args.index("--min-caption-width")
        min_caption_width = float(args[i + 1])
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__)
        sys.exit(1)

    doc = lib.open_doc(args[0])
    print(f"pages: {doc.page_count}\n")

    blocks = lib.page_blocks(doc)
    area = lib.content_area(blocks)
    col_edges = lib.column_left_edges(blocks)
    two_column = lib.is_two_column_doc(col_edges, doc[0].rect.width)
    print(f"body content area: {tuple(round(v, 1) for v in area) if area else None}")
    print(f"body column left edge(s): {[round(e, 1) for e in col_edges]} "
          f"(-> treated as {'two-column' if two_column else 'single-column'} for crop bounds)")
    print("(crops are bounded by these -- a wildly wrong content area means "
          "the crop heuristics will be wrong too)\n")

    for pno, page in enumerate(doc, start=1):
        imgs = page.get_images(full=True)
        drawings = page.get_drawings()
        if not imgs and not drawings:
            continue
        visible = lib.visible_drawing_rects(page)
        print(f"--- page {pno}: {len(imgs)} embedded raster image(s), "
              f"{len(drawings)} vector drawing item(s), "
              f"{len(visible)} of them visible after clipping")
        for img in imgs:
            xref = img[0]
            info = doc.extract_image(xref)
            rects = page.get_image_rects(xref)
            print(f"    xref={xref} ext={info['ext']} w={info['width']} h={info['height']} "
                  f"rects={[tuple(round(v, 1) for v in r) for r in rects]}")

    print(f"\nDetected captions (min-caption-width={min_caption_width}):")
    captions = lib.find_captions(doc, min_caption_width=min_caption_width)
    for c in captions:
        print(f"  page={c['page']} kind={c['kind']} num={c['num']} "
              f"bbox={tuple(round(v, 1) for v in c['bbox'])}")
        print(f"    {c['text'][:180]}")

    if not captions:
        # The default threshold (400) is above the caption width of plenty of
        # real papers -- a 396pt caption block filters out to zero and looks
        # exactly like "this paper has no captions". Rather than make the
        # reader go to dump_blocks.py to discover that, re-run the detection
        # with no width floor and report what floor would actually work.
        unfiltered = lib.find_captions(doc, min_caption_width=0)
        if unfiltered:
            widest = max(c["bbox"][2] - c["bbox"][0] for c in unfiltered)
            suggest = max(50.0, round((widest * 0.6) / 10) * 10)
            print(f"\n0 visual(s) detected at min-caption-width={min_caption_width}, but "
                  f"{len(unfiltered)} caption block(s) match with no width floor.")
            print(f"  Widest of those is {widest:.0f}pt -- the threshold is what "
                  f"filtered them out, not the paper.")
            print(f"  Re-run inspect_pdf.py and build_manifest.py with "
                  f"--min-caption-width {suggest:.0f} (confirm with dump_blocks.py "
                  f"that these really are captions and not noise).")
            return
        print("\n0 visual(s) detected, and none match even with no width floor.")
        print("  Either this paper captions its visuals unusually (check for "
              "'Fig.' abbreviations or non-English captions and extend the regex "
              "in pdf_parser_lib.find_captions), or -- if the pages above showed "
              "near-zero drawings and no text -- it's a scanned PDF needing OCR.")
        return

    print(f"\n{len(captions)} visual(s) detected. Next: run build_manifest.py.")
    print("If a page's layout looks unusual (two-column, floating figures, "
          "captions above the visual instead of below), dump its text blocks "
          "with dump_blocks.py before trusting the automatic crop heuristic.")


if __name__ == "__main__":
    main()
