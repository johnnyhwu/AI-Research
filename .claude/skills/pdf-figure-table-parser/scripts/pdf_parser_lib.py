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

CAPTION_RE = re.compile(r"^(Figure|Fig\.?|Table)\s+(\d+)", re.IGNORECASE)


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
    Locate every 'Figure N' / 'Fig. N' / 'Table N' caption in the document.

    A caption is a text block that STARTS with "Figure N" / "Fig. N" /
    "Table N" (no comma right after the number -- that pattern means the
    sentence is an inline cross-reference like "Table 2, Figure 3, and Table
    3 test ...", not the caption itself). When the same (kind, num) is
    matched by more than one block -- which happens because papers also
    refer to visuals in running prose -- the longest matching block wins,
    since the real caption is always the fullest description. A minimum
    width filter guards against narrow incidental matches.

    "Figure"/"Fig."/"fig" all normalize to kind "figure" so a paper that
    abbreviates its captions doesn't get treated as a different visual type.
    The exact matched prefix (e.g. "Fig. 1") is kept separately as "label",
    since that's the literal string this paper actually uses when
    cross-referencing the same visual elsewhere in the body -- needed by
    find_nearby_text, which must search for the paper's own phrasing rather
    than an assumed spelled-out "Figure N".
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
            kind = "figure" if m.group(1).lower().startswith("fig") else "table"
            key = (kind, int(m.group(2)))
            entry = {
                "page": pno,
                "bbox": (x0, y0, x1, y1),
                "kind": key[0],
                "num": key[1],
                "label": norm(clean[:m.end()]),
                "text": norm(clean),
                # A real caption separates the label from its description with
                # ":" or "." ("Table 1: Generation quality ..."); a sentence that
                # merely opens with the label runs straight on into prose
                # ("Table 1 and Figure 3 reveal a cross-over ..."). That prose
                # sentence is often the *longer* block, so the separator has to
                # outrank length -- otherwise the cross-reference wins.
                # A pipe or dash separator ("Figure 1 | Performance landscape
                # ...") is the same signal in a different house style, and is
                # common enough that leaving it out lets a cross-reference win
                # the tie-break on length alone. The separator may or may not
                # be preceded by a space, so look past one.
                "separated": clean[m.end():].lstrip()[:1] in (":", ".", "|", "—", "–"),
                # A second, weaker signal for the same problem: some caption
                # styles put the number on its own line ("Figure 2\nCross-domain
                # transfer results.") with no ":"/"." right after it, so
                # "separated" alone can't tell that apart from an inline
                # reference like "Figure 2 shows that ...". But a real caption's
                # title starts with a capitalized word right after the number;
                # a run-on sentence continues in lowercase ("shows", "is",
                # "demonstrates"). Only used as a tie-break under "separated".
                "title_like": (lambda w: bool(w) and w[0].isupper())(clean[m.end():].lstrip()),
            }
            prev = candidates.get(key)
            rank = (entry["separated"], entry["title_like"], len(entry["text"]))
            prev_rank = (prev["separated"], prev["title_like"], len(prev["text"])) if prev else None
            if prev is None or rank > prev_rank:
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


def prose_blocks(blocks, column_width=None, min_chars=100, width_frac=0.75):
    """
    The subset of `blocks` that reads as running body prose: long *and* about
    as wide as the document's own text column.

    Both conditions are needed. Length alone lets a dense table row through
    (they're easily 100+ characters); width alone lets a section heading
    through. Used for two things: deriving the page's live content area
    (content_area) and stopping a figure's crop from swallowing the
    paragraph above it (auto_crop_top).
    """
    if column_width is None:
        column_width = estimate_column_width(blocks)
    out = []
    for b in blocks:
        if len(b["text"]) < min_chars:
            continue
        if column_width is not None and (b["bbox"][2] - b["bbox"][0]) < column_width * width_frac:
            continue
        out.append(b)
    return out


def column_left_edges(blocks, tol=2.0, min_share=0.1, min_count=3):
    """
    The x-coordinates at which this document's body text columns start --
    one value for a single-column paper, two for a two-column one -- found by
    clustering where its prose blocks repeatedly line up.

    A column edge is used by *most* of the document's prose, so clusters are
    kept only if they account for at least `min_share` of it. Without that,
    the indent of a wide table's first column (dense enough to pass as prose)
    registers as a second "column edge" and every figure on the page starts
    getting bounded by table rows.
    """
    xs = sorted(b["bbox"][0] for b in prose_blocks(blocks))
    if not xs:
        return []
    # Anchored, not chained: each value must be within tol of the cluster's
    # first member. Chaining off the running last member lets a run of
    # closely-spaced table indents (138.6, 140.0, 141.6, 143.3, ...) merge
    # into one wide cluster that then passes the share test and gets treated
    # as a real column edge.
    clusters, current = [], [xs[0]]
    for x in xs[1:]:
        if x - current[0] <= tol:
            current.append(x)
        else:
            clusters.append(current)
            current = [x]
    clusters.append(current)
    threshold = max(min_count, min_share * len(xs))
    return [statistics.median(c) for c in clusters if len(c) >= threshold]


def flush_left_blocks(blocks, edges, column_width=None, tol=2.0, min_width_frac=0.35):
    """
    Text blocks that start exactly on a body-column's left edge and are wide
    enough to be a real line of it -- body paragraphs, section headings,
    running headers.

    This is the signal `auto_crop_top` uses to know it has walked out of a
    figure and into the page's text flow. Exact left-edge alignment is what
    does most of the work: a figure's own internal text (panel labels,
    callouts, quoted model output) is centred or indented inside the figure
    and lands a few points off the column edge, so a tight `tol` separates
    the two cleanly. Widening `tol` past ~2pt starts pulling figure-internal
    text in and will crop figures to nothing -- use --crop-top-override
    instead if a document needs that.

    The width test catches what alignment alone misses: a subfigure label
    "(a)" sitting at the far left of a figure can land within a point of the
    column edge by coincidence, and treating that as the body-text boundary
    would slice the figure in half.

    Deliberately not the same test as `prose_blocks`: a section heading is
    too short to read as prose but is every bit as much a boundary, and
    conversely a dense table row reads as prose but is indented off the
    column edge and must *not* act as a boundary.
    """
    if column_width is None:
        column_width = estimate_column_width(blocks)
    min_width = column_width * min_width_frac if column_width else 0.0
    out = []
    for b in blocks:
        if (b["bbox"][2] - b["bbox"][0]) < min_width:
            continue
        if any(abs(b["bbox"][0] - e) <= tol for e in edges):
            out.append(b)
    return out


def content_area(blocks, quantile=0.05):
    """
    The rectangle the document actually prints its body inside, derived from
    where its own prose blocks sit -- no hardcoded page geometry, so it
    adapts to whatever margins the paper's template uses.

    Two crop bugs are fixed by knowing this rectangle:

    - **Running headers/footers.** They live *outside* this rectangle (above
      `y0`, below `y1`), so using `y0` as the top-of-content margin keeps a
      page-top figure's crop from starting on "12 Collins, Bolton, Nguyen et
      al.".
    - **Ink that is drawn but never shown.** A figure that embeds a
      screenshot commonly places the raster far outside the page and relies
      on a clipping path to show only a window of it. `visible_drawing_rects`
      recovers the true extent for vector drawings, but PyMuPDF exposes no
      clip information for placed *images*, so an image bbox can claim to
      cover the right margin (or run off the page entirely) when nothing of
      it is visible there. Gating image bboxes on this rectangle -- widened
      by a tolerance, since figures legitimately bleed a few points into the
      margin -- throws those phantoms out.

    x-bounds use a 5% quantile rather than min/max so one stray wide block
    (a full-bleed float, a mis-measured ligature) can't inflate the area;
    y-bounds use the true extremes, since the topmost and bottommost prose on
    *some* page is exactly the live text band's edge.

    Returns a pymupdf.Rect, or None if the document has too little prose to
    measure (a slide deck, a poster) -- callers must handle None by falling
    back to page-level bounds.
    """
    prose = prose_blocks(blocks)
    if len(prose) < 5:
        return None
    xs0 = sorted(b["bbox"][0] for b in prose)
    xs1 = sorted(b["bbox"][2] for b in prose)

    def q(vals, p):
        return vals[int(p * (len(vals) - 1))]

    return pymupdf.Rect(
        q(xs0, quantile),
        min(b["bbox"][1] for b in prose),
        q(xs1, 1.0 - quantile),
        max(b["bbox"][3] for b in prose),
    )


def visible_drawing_rects(page):
    """
    Every vector drawing on the page, as the bbox of the part that is
    *actually visible* -- its path bbox intersected with the clipping path in
    effect when it was drawn.

    `page.get_drawings()` reports the raw path bbox, which is a trap for crop
    geometry: a figure built from a clipped screenshot routinely has paths
    extending hundreds of points past the page edge (bboxes like
    x=(-310, 681) on a 612pt-wide page are normal), all of it invisible.
    Taking min/max over those bboxes blows a figure's crop out to the full
    page width, padding the render with blank margin and shrinking the
    figure. `page.get_drawings(extended=True)` additionally emits the `clip`
    and `group` entries with the scissor rect and a nesting `level`, which is
    everything needed to replay the clip stack and recover the visible
    extent.

    Entries clipped away to nothing are dropped, not returned as empty rects.
    """
    out = []
    stack = []  # (level, clip rect), innermost last
    for d in page.get_drawings(extended=True):
        level = d.get("level") or 0
        while stack and stack[-1][0] >= level:
            stack.pop()
        if d["type"] in ("clip", "group"):
            clip = d.get("scissor") or d.get("rect")
            if clip is not None:
                stack.append((level, pymupdf.Rect(clip)))
            continue
        rect = pymupdf.Rect(d["rect"])
        for _, clip in stack:
            rect &= clip
        if rect.is_empty or rect.is_infinite:
            continue
        out.append(rect)
    return out


def visual_ink_rects(page, content_rect=None, tol_frac=0.04):
    """
    Where this page's visual content actually puts ink: clip-corrected vector
    drawings plus placed raster images, all clamped to what a reader can see.

    This is the ground truth both crop heuristics run on -- auto_crop_top for
    the vertical boundary, auto_crop_hbounds for the horizontal one.

    Drawings come from visible_drawing_rects (exact, via the clip stack).
    Images get the cruder treatment because PyMuPDF reports no clip for them:
    an image placed partly off-page is dropped outright (it is being used as
    a clipped backdrop, and its bbox describes the uncropped source, not what
    shows), and what survives is gated on `content_rect` widened by
    `tol_frac` of the page width. That tolerance is what lets a figure bleed
    slightly into the margin while still rejecting a raster whose bbox claims
    the whole margin. If a document genuinely runs figures far into its
    margins, that gate is the thing to loosen -- or bypass it entirely with
    build_manifest.py's --margin-x.
    """
    page_rect = page.rect
    if content_rect is not None:
        tol = page_rect.width * tol_frac
        gate = pymupdf.Rect(content_rect.x0 - tol, page_rect.y0,
                            content_rect.x1 + tol, page_rect.y1)
    else:
        gate = page_rect

    out = []
    for rect in visible_drawing_rects(page):
        rect = rect & gate
        if not rect.is_empty:
            out.append(rect)
    for info in page.get_image_info():
        rect = pymupdf.Rect(info["bbox"])
        if rect.x1 < rect.x0 or rect.y1 < rect.y0:
            continue
        if not page_rect.contains(rect):
            continue  # clipped backdrop: bbox describes the source, not what shows
        rect = rect & gate
        if not rect.is_empty:
            out.append(rect)
    return out


def is_two_column_doc(col_edges, page_width, gap_frac=0.25):
    """
    Whether this document actually has a two-column body layout, from the
    document-wide `column_left_edges(...)` clusters: real if the widest and
    narrowest edge differ by more than `gap_frac` of the page width (a real
    second column starts well past the page's midpoint), not merely because
    there's more than one cluster -- a single-column paper's nested-list
    indentation also produces two close-together edges (e.g. 70.9 and 90.2,
    ~19pt apart on a 612pt page), and treating that as "two columns" is what
    makes `caption_column` misclassify a narrow, centered single-column
    caption as living in a half-page column it doesn't actually share with
    anything -- see `caption_column`'s `two_column` parameter.
    """
    if len(col_edges) < 2:
        return False
    return (max(col_edges) - min(col_edges)) > page_width * gap_frac


def rects_in_column(rects, caption_bbox, page_width, col_tol=15.0, two_column=True):
    """
    Restrict ink rects to the column the caption sits in, so a side-by-side
    neighbour's ink can't be mistaken for this visual's own. A full-width
    caption keeps everything. Mirrors auto_crop_hbounds' in_column test.

    `two_column` should be `is_two_column_doc(...)` for the whole document --
    see `caption_column`.
    """
    col = caption_column(caption_bbox, page_width, two_column=two_column)
    if col == "full":
        return list(rects)
    mid = page_width / 2.0
    if col == "left":
        return [r for r in rects if r.x1 <= mid + col_tol]
    return [r for r in rects if r.x0 >= mid - col_tol]


def caption_column(bbox, page_width, full_width_frac=0.55, two_column=True):
    """
    Classify a caption/rect bbox as 'left', 'right', or 'full' relative to a
    two-column page layout, purely from its own horizontal extent -- no
    hardcoded column geometry, so it works across differently-sized pages.

    A bbox wide enough to plausibly span both columns (>= full_width_frac of
    the page width) is 'full'; otherwise it's classified by which half of
    the page its center falls in. Used to keep same-page, opposite-column
    visuals from contaminating each other's crop bounds (see auto_crop_top
    and auto_crop_hbounds below).

    `two_column` must be supplied by the caller (typically
    `is_two_column_doc(column_left_edges(...), page_width)`, computed once
    for the whole document) and short-circuits straight to 'full' when
    false. Without this, a **single-column** paper with a short, centered
    caption -- narrower than `full_width_frac` of the page purely because
    it's a one-line caption, not because the document is two-column at all
    -- gets its midpoint compared against the raw page center and is
    misclassified as living in a "left" or "right" column. Everything
    downstream then wrongly excludes that visual's own wider content (table
    cells, chart ink) sitting past that arbitrary midpoint, clipping both
    outer edges of the crop. This happened for real on two single-line-
    caption, ruleless tables in one paper -- see `auto_crop_hbounds`.
    """
    if not two_column:
        return "full"
    x0, x1 = bbox[0], bbox[2]
    mid = page_width / 2.0
    if (x1 - x0) >= page_width * full_width_frac:
        return "full"
    return "left" if (x0 + x1) / 2.0 < mid else "right"


def auto_crop_top(page_no, caption_bbox, captions_by_page, page_width,
                  default_margin=58.0, ink_rects=None, barriers=None,
                  text_blocks=None, kind="figure", max_gap=36.0, pad=6.0,
                  two_column=True):
    """
    Top boundary for a visual's region, in two stages: a conservative *floor*
    that nothing above may be crossed, then a tightening step that walks the
    visual's own ink upward from the caption.

    The floor is the highest (numerically largest y) of:

    - `default_margin` -- the top of the page's live content. Pass
      `content_area(...).y0` here rather than a page-edge constant, so a
      figure at the top of a page doesn't start its crop on the running
      header.
    - the bottom edge of the nearest *other caption* above this one, on the
      same page and in the same column (e.g. Table 3 starts right after Table
      2's caption ends). Column-aware: a single-column caption ignores
      captions in the opposite column, which would otherwise sit higher on
      the page and chop this visual down to nothing. Full-width captions
      bound either column.
    - the bottom edge of the lowest `barriers` block above the caption in the
      same column -- body text flush with a column's left edge, per
      `flush_left_blocks`. This is what stops a figure that floats mid-page
      (body text above it, caption below) from cropping the whole upper half
      of the page, and it also keeps a page-top figure off the running
      header. For tables, only barriers that are also body prose count: a
      table indented off the column edge is the normal case this handles
      safely, but a table typeset flush left would otherwise bound itself
      away to nothing, and being conservative there is the older, safer
      behaviour.

    The tightening step then starts at the *lowest* ink above the caption and
    repeatedly absorbs any ink rect that reaches within `max_gap` of the
    region so far, stopping at the first real whitespace gap. That is what
    actually removes the blank band between the floor and the figure, and it
    is robust to the inline icons some papers drop into body text and section
    headings -- those sit above the gap, so the walk never reaches them. Ink
    for a single-column caption should be filtered with rects_in_column first.

    Seeding on the lowest ink rather than on the caption matters: a figure
    whose bottom row is a text label ("(a) Single-turn  (b) Multi-turn") can
    easily leave 25pt between its last drawn ink and its caption, and a walk
    seeded at the caption would never reach the figure at all.

    Falls back to the floor when there is no ink at all in the region (a
    figure drawn purely as text, a ruleless table).
    """
    cap_y0 = caption_bbox[1]
    target_col = caption_column(caption_bbox, page_width, two_column=two_column)

    def same_column(bbox):
        # A full-width visual spans both columns, so anything on the page can
        # bound it. A single-column one is only bounded by its own column and
        # by full-width blocks.
        if target_col == "full":
            return True
        col = caption_column(bbox, page_width, two_column=two_column)
        return col == "full" or col == target_col

    floor = default_margin
    for other in captions_by_page.get(page_no, []):
        if other["bbox"] == caption_bbox or not same_column(other["bbox"]):
            continue
        if other["bbox"][3] < cap_y0:
            floor = max(floor, other["bbox"][3] + 8.0)

    for b in barriers or []:
        if b["page"] != page_no or not same_column(b["bbox"]):
            continue
        if kind == "table" and not b.get("is_prose"):
            continue
        if b["bbox"][3] < cap_y0:
            floor = max(floor, b["bbox"][3] + 8.0)

    # A boundary must never land inside a block of text. A wrapped section
    # heading is the usual culprit: only its first line starts on the column
    # edge, so the barrier's 8pt clearance lands between the two lines and the
    # continuation (plus any inline icon on it) ends up inside the crop.
    # This only ever runs from a floor a barrier put there, so it cannot walk
    # into a figure: the bounded retry exists for a heading that wraps to more
    # than two lines, not to chase text down the page.
    for _ in range(5):
        pushed = False
        for b in text_blocks or []:
            if b["page"] != page_no or not same_column(b["bbox"]):
                continue
            if b["bbox"][1] < floor < b["bbox"][3] < cap_y0:
                floor = b["bbox"][3] + 8.0
                pushed = True
        if not pushed:
            break

    band = [r for r in (ink_rects or []) if r.y1 <= cap_y0 and r.y1 > floor]
    if not band:
        return floor

    top = max(r.y1 for r in band)
    grew = True
    while grew:
        grew = False
        for r in band:
            if r.y0 < top and r.y1 >= top - max_gap:
                top = r.y0
                grew = True
    return max(floor, top - pad)


def auto_crop_hbounds(page, top, bottom, caption_bbox, ink_rects=None, text_rects=None,
                      pad=8.0, min_width=40.0, band_tol=2.0, col_tol=15.0, two_column=True):
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

    Column-aware on top of that: two single-column visuals that sit side by
    side (e.g. a table in the left column and a figure in the right column,
    both spanning the same y-range) would otherwise both see each other's
    drawings within the shared vertical band, blowing each one's width out
    to near-full-page. When the target caption is single-column, candidate
    drawings/images are restricted to the same side of the page (with a
    small col_tol so ink that legitimately abuts the column gutter isn't
    excluded); a full-width caption's band isn't restricted, since it's
    meant to span both columns.

    Always returns (x0, x1): the caption's own bbox is the floor, widened by
    any drawings/images *and text blocks* found in the band above/below it.
    Text blocks matter because a **ruleless table (no drawn gridlines at
    all) with a short, centered caption** has no vector ink whatsoever in its
    band -- without also looking at text, the crop would collapse to just the
    caption's own (often much narrower) width and silently clip the table's
    outer columns on both sides. This bit only once: two single-line-caption
    tables in one paper ("Table 4 Lifecycle operations...", "Table 6
    Principal MSCE hyperparameters.") both rendered looking like ordinary,
    correctly-sized crops -- nothing in `crop_warnings` catches a narrow
    *width*, only a narrow height -- and only turned out wrong on a direct
    visual check. Since [top, bottom] is already finalized by the time this
    runs (by the auto heuristic or an explicit override), any text block
    still inside that band is presumably part of the visual itself (table
    cells, axis labels, panel titles) rather than stray prose, which is
    already excluded upstream when the vertical bounds are picked.

    Candidates come from `visual_ink_rects`, which has already corrected each
    drawing to its clipped (visible) extent and discarded off-page raster
    backdrops. Feeding raw `page.get_drawings()` bboxes in here instead is
    what used to stretch a figure's crop to the full page width on any paper
    that clips embedded screenshots.
    """
    page_w = page.rect.width
    col = caption_column(caption_bbox, page_w, two_column=two_column)
    mid = page_w / 2.0

    if ink_rects is None:
        ink_rects = visual_ink_rects(page)
    if text_rects is None:
        text_rects = [pymupdf.Rect(b[:4]) for b in page.get_text("blocks")]

    def in_column(r):
        if col == "full":
            return True
        if col == "left":
            return r.x1 <= mid + col_tol
        return r.x0 >= mid - col_tol

    rects = [pymupdf.Rect(caption_bbox)]
    for r in list(ink_rects) + list(text_rects):
        # Full containment, not mere overlap -- a page-spanning
        # decorative/background rect can poke into the band at one edge
        # without actually being part of this visual, and would otherwise
        # blow the crop out to near-full-page width.
        if r.y0 >= top - band_tol and r.y1 <= bottom + band_tol and in_column(r):
            rects.append(r)
    x0 = min(r.x0 for r in rects)
    x1 = max(r.x1 for r in rects)
    if x1 - x0 < min_width:
        return None
    return max(0.0, x0 - pad), min(page_w, x1 + pad)


def crop_warnings(rect, page_no, prose, kind="figure", min_dim=24.0, prose_frac=0.25):
    """
    Text-only sanity checks on a crop rectangle, so a wrong region gets
    flagged instead of silently shipped as a confident-looking PNG (this
    repo's "fail loud, not silent" rule). Returns a list of human-readable
    warning strings; empty means nothing looked wrong.

    Two things are checked:

    - A degenerate rectangle. Usually means the caption sits *above* its
      visual (the academic-table convention) so the default "crop everything
      between the content top and the caption" region is empty page. The fix
      is --crop-top-override plus --crop-bottom-override; see SKILL.md.
    - A crop whose height is mostly body prose. Means the top boundary ran
      away and swallowed the paragraph above the figure. Figures only:
      a table's own rows legitimately read as prose, so the check would fire
      on every correctly-cropped table.
    """
    warnings = []
    if rect.width < min_dim or rect.height < min_dim:
        warnings.append(f"degenerate crop region ({rect.width:.0f}x{rect.height:.0f}pt) -- "
                        "caption is probably above its visual; see SKILL.md on "
                        "--crop-top-override + --crop-bottom-override")
    if kind != "table" and rect.height > 0:
        covered = 0.0
        for b in prose or []:
            if b["page"] != page_no:
                continue
            overlap = pymupdf.Rect(b["bbox"]) & rect
            if not overlap.is_empty:
                covered += overlap.height
        if covered > prose_frac * rect.height:
            warnings.append(f"{covered / rect.height:.0%} of the crop height is body prose -- "
                            "the top boundary probably overshot; check dump_blocks.py "
                            "and pass --crop-top-override")
    return warnings


def find_nearby_text(blocks, caption_bboxes, label, window_before=80, window_after=220):
    """
    First mention of the visual's own caption label (e.g. "Figure 3" or
    "Fig. 3", exactly as the paper phrases it) in the document body outside
    of the caption itself -- gives Step-3-style downstream consumers context
    for why the visual is referenced. None if no such mention exists.
    """
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
        f.write("\n")
