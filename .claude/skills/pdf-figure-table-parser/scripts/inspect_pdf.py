#!/usr/bin/env python3
"""
Dry-run a PDF before extracting anything: page count, embedded raster image
counts, vector-drawing counts per page, and every Figure/Table caption it can
detect (with page + bounding box). Read this output as TEXT -- do not open
the PDF or any rendered image in an image viewer / Read tool to "double
check"; that defeats the whole point of this pipeline.

Usage:
    python inspect_pdf.py <pdf_path>
"""
import sys
import pdf_parser_lib as lib


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    doc = lib.open_doc(sys.argv[1])
    print(f"pages: {doc.page_count}\n")

    for pno, page in enumerate(doc, start=1):
        imgs = page.get_images(full=True)
        drawings = page.get_drawings()
        if not imgs and not drawings:
            continue
        print(f"--- page {pno}: {len(imgs)} embedded raster image(s), "
              f"{len(drawings)} vector drawing item(s)")
        for img in imgs:
            xref = img[0]
            info = doc.extract_image(xref)
            rects = page.get_image_rects(xref)
            print(f"    xref={xref} ext={info['ext']} w={info['width']} h={info['height']} "
                  f"rects={[tuple(round(v, 1) for v in r) for r in rects]}")

    print("\nDetected captions:")
    captions = lib.find_captions(doc)
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
