"""
Shared logic for extracting figures/tables out of a born-digital PDF without
ever needing an agent (or a human) to look at the rendered images.

Used by inspect_pdf.py, build_manifest.py and verify_manifest.py. See
../SKILL.md for the workflow this supports.
"""
import re
import statistics
import hashlib
import json
import os

import pymupdf

CAPTION_RE = re.compile(r"^(Figure|Table)\s+(\d+)", re.IGNORECASE)


def norm(text):
    return " ".join(text.split())


def open_doc(pdf_path):
    return pymupdf.open(pdf_path)


def page_blocks(doc):
    """All text blocks in the doc as flat dicts: page (1-indexed), bbox, text."""
    out = []
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            out.append({"page": pno, "bbox": (x0, y0, x1, y1), "text": norm(text)})
    return out


def find_captions(doc, min_caption_width=400):
    """
    Locate every 'Figure N' / 'Table N' caption in the document.

    A caption is a text block that STARTS with "Figure N" / "Table N" (no
    comma right after the number -- that pattern means the sentence is an
    inline cross-reference like "Table 2, Figure 3, and Table 3 test ...",
    not the caption itself). When the same (kind, num) is matched by more
    than one block -- which happens because papers also refer to visuals in
    running prose -- the longest matching block wins, since the real caption
    is always the fullest description. A minimum width filter guards against
    narrow incidental matches.
    """
    candidates = {}
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
            clean = text.strip()
            m = CAPTION_RE.match(clean)
            if not m:
                continue
            if clean[m.end():m.end() + 1] == ",":
                continue  # inline cross-reference, e.g. "Table 2, Figure 3, and ..."
            key = (m.group(1).lower(), int(m.group(2)))
            entry = {
                "page": pno,
                "bbox": (x0, y0, x1, y1),
                "kind": key[0],
                "num": key[1],
                "text": norm(clean),
            }
            if key not in candidates or len(entry["text"]) > len(candidates[key]["text"]):
                candidates[key] = entry

    captions = [c for c in candidates.values() if (c["bbox"][2] - c["bbox"][0]) >= min_caption_width]
    captions.sort(key=lambda c: (c["page"], c["bbox"][1]))
    return captions


def estimate_column_width(blocks):
    """
    Median width of blocks that look like body prose (long text), used to
    tell a 'full paragraph' block apart from a narrow figure-internal label
    (axis tick, legend entry, etc). Works for single- or double-column
    layouts since it's derived from the actual document, not hardcoded.
    """
    widths = [b["bbox"][2] - b["bbox"][0] for b in blocks if len(b["text"]) > 100]
    if not widths:
        return None
    return statistics.median(widths)


def auto_crop_top(page_no, caption_bbox, captions_by_page, default_margin=58.0):
    """
    Heuristic top boundary for a visual's region: the bottom edge of the
    nearest *other caption* above this one on the same page, if any (e.g.
    Table 3 starts right after Table 2's caption ends). Falls back to a
    fixed top-of-content margin when there's no such caption -- the common
    case of a visual sitting at the top of a page, right after a page break.

    Deliberately anchors only on other captions, not on generic "paragraph
    looking" text blocks: a table's own row text or a figure's own internal
    labels can easily look like a paragraph (wide, many characters) and
    would otherwise get mistaken for the boundary, cropping almost nothing.
    Captions are a much safer signal since they're already positively
    identified by find_captions().

    This assumes the common academic-paper convention of floats sitting at
    the top of a page (or stacked back-to-back down a page) rather than
    floating mid-column with body text both above and below. For that
    layout, or two-column papers, inspect with dump_blocks.py (via
    inspect_pdf.py) and pass an explicit --crop-top-override instead of
    trusting this heuristic blindly.
    """
    cap_y0 = caption_bbox[1]
    best_y1 = None
    for other in captions_by_page.get(page_no, []):
        if other["bbox"] == caption_bbox:
            continue
        y1 = other["bbox"][3]
        if y1 < cap_y0 and (best_y1 is None or y1 > best_y1):
            best_y1 = y1
    if best_y1 is None:
        return default_margin
    return best_y1 + 8.0


def auto_crop_hbounds(page, top, bottom, caption_bbox, pad=8.0, min_width=40.0, band_tol=2.0):
    """
    Tight horizontal bounds for a visual's region, derived from the actual
    vector drawings / raster images sitting in its vertical band [top,
    bottom] on the page -- ground truth for where the visual's ink actually
    is, unlike a single global column-width guess.

    Needed for papers that mix full-width and single-column floats in a
    two-column layout (common in academic PDFs): a fixed per-page margin
    computed from the median single-column text width crops full-width
    tables down to one column's width, and conversely a full-width margin
    leaves single-column figures swimming in blank space or bleeding into
    the other column. Reading the region's own drawing/image bboxes sidesteps
    guessing which case applies.

    Always returns (x0, x1): the caption's own bbox is the floor (a
    ruleless table with no drawn lines -- e.g. no gridlines at all -- still
    has to crop *something*, and the caption's width is the only reliable
    signal left in that case), widened by any drawings/images found in the
    band above/below it.
    """
    rects = [pymupdf.Rect(caption_bbox)]
    for d in page.get_drawings():
        r = d["rect"]
        if r.x1 < r.x0 or r.y1 < r.y0:
            continue  # reversed/invalid rect, not just a zero-thickness ruling line
        if r.y0 >= top - band_tol and r.y1 <= bottom + band_tol:
            # Full containment, not mere overlap -- a page-spanning
            # decorative/background rect can poke into the band at one edge
            # without actually being part of this visual, and would
            # otherwise blow the crop out to near-full-page width.
            rects.append(r)
    for info in page.get_image_info():
        r = pymupdf.Rect(info["bbox"])
        if r.x1 < r.x0 or r.y1 < r.y0:
            continue  # reversed/invalid rect, not just a zero-thickness ruling line
        if r.y0 >= top - band_tol and r.y1 <= bottom + band_tol:
            rects.append(r)
    x0 = min(r.x0 for r in rects)
    x1 = max(r.x1 for r in rects)
    if x1 - x0 < min_width:
        return None
    page_w = page.rect.width
    return max(0.0, x0 - pad), min(page_w, x1 + pad)


def find_nearby_text(blocks, caption_bboxes, kind, num, window_before=80, window_after=220):
    """
    First mention of 'Figure N' / 'Table N' in the document body outside of
    the caption itself -- gives Step-3-style downstream consumers context
    for why the visual is referenced. None if no such mention exists.
    """
    label = f"{kind.capitalize()} {num}"
    for blk in blocks:
        if (blk["page"], blk["bbox"]) in caption_bboxes:
            continue
        idx = blk["text"].find(label)
        if idx == -1:
            continue
        start = max(0, idx - window_before)
        end = min(len(blk["text"]), idx + window_after)
        return blk["text"][start:end].strip()
    return None


def render_crop(page, rect, out_path, zoom=3.0):
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, clip=rect)
    pix.save(out_path)
    return pix.width, pix.height


def verify_manifest(manifest, repo_root):
    """
    Programmatic sanity checks -- never open the images themselves to do
    this, just stat() them and inspect the JSON. Returns a list of error
    strings; empty list means everything passed.
    """
    errors = []
    required_keys = {"id", "file", "type", "page", "caption", "nearby_text", "parser_confidence"}

    if "source_pdf" not in manifest or "images" not in manifest:
        return ["manifest missing top-level 'source_pdf' or 'images' key"]

    ids, files, hashes = set(), set(), {}
    for entry in manifest["images"]:
        eid = entry.get("id", "<no id>")
        missing = required_keys - set(entry.keys())
        if missing:
            errors.append(f"{eid}: missing keys {missing}")
        if entry.get("id") in ids:
            errors.append(f"duplicate id {entry.get('id')}")
        ids.add(entry.get("id"))
        if entry.get("file") in files:
            errors.append(f"duplicate file path {entry.get('file')}")
        files.add(entry.get("file"))

        f = entry.get("file")
        abspath = os.path.join(repo_root, f) if f else None
        if not abspath or not os.path.isfile(abspath):
            errors.append(f"{eid}: file does not exist: {abspath}")
            continue
        size = os.path.getsize(abspath)
        if size == 0:
            errors.append(f"{eid}: file is zero bytes")
        h = hashlib.sha256(open(abspath, "rb").read()).hexdigest()
        if h in hashes:
            errors.append(f"{eid}: content-duplicate of {hashes[h]}")
        hashes[h] = eid

        if entry.get("type") not in ("figure", "table", "diagram", "other"):
            errors.append(f"{eid}: bad type {entry.get('type')!r}")
        if entry.get("parser_confidence") not in ("high", "low"):
            errors.append(f"{eid}: bad parser_confidence {entry.get('parser_confidence')!r}")

    return errors


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
