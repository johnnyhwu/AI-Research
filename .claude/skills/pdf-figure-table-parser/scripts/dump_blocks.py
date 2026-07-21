#!/usr/bin/env python3
"""
Dump every text block's bounding box + text on specific pages, sorted
top-to-bottom. Use this when a page's layout is unusual and you need to
manually figure out where a figure/table region actually starts (pass the
result to build_manifest.py's --crop-top-override).

Usage:
    python dump_blocks.py <pdf_path> <page_num> [<page_num> ...]
"""
import sys
import pymupdf


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    doc = pymupdf.open(sys.argv[1])
    pages = [int(p) for p in sys.argv[2:]]

    for pno in pages:
        page = doc[pno - 1]
        print(f"===== PAGE {pno} (rect={page.rect}) =====")
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: b[1])
        for b in blocks:
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            text = " ".join(text.split())
            print(f"  y=({y0:.1f},{y1:.1f}) x=({x0:.1f},{x1:.1f}) : {text[:100]}")


if __name__ == "__main__":
    main()
