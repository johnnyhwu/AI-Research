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
    print(f"body content area: {tuple(round(v, 1) for v in area) if area else None}")
    print(f"body column left edge(s): {[round(e, 1) for e in lib.column_left_edges(blocks)]}")
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

    print(f"\n{len(captions)} visual(s) detected. Next: run build_manifest.py.")
    print("If a page's layout looks unusual (two-column, floating figures, "
          "captions above the visual instead of below), dump its text blocks "
          "with dump_blocks.py before trusting the automatic crop heuristic.")


if __name__ == "__main__":
    main()
