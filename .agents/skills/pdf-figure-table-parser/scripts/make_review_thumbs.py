#!/usr/bin/env python3
"""
Write downscaled JPEG copies of every image in a manifest, for a visual check
that keeps full-size pixels out of the main context. Hand the output folder to
a subagent (see SKILL.md, "Visual check"); don't open the thumbnails yourself.

Run from the repo root.

Usage:
    python make_review_thumbs.py <image-manifest.json> <out_dir> [--max-side 900]
"""
import argparse
import json
import os

from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("out_dir")
    ap.add_argument("--max-side", type=int, default=900)
    args = ap.parse_args()

    with open(args.manifest, encoding="utf-8") as f:
        images = json.load(f)["images"]
    os.makedirs(args.out_dir, exist_ok=True)
    for entry in images:
        out = os.path.join(args.out_dir, f"{entry['id']}.jpg")
        im = Image.open(entry["file"]).convert("RGB")
        full = im.size
        im.thumbnail((args.max_side, args.max_side))
        im.save(out, quality=70)
        print(f"{out}\t{entry['id']}\t{full[0]}x{full[1]}px\t{entry['caption'][:70]}")


if __name__ == "__main__":
    main()
