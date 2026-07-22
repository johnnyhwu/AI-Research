#!/usr/bin/env python3
"""
Quality-check an article.md produced by the blog-writer skill. Pure text/JSON
inspection -- never opens any image, and doesn't need the source PDF either.

Checks:
  - the trailing ```figure-map``` fenced block is valid JSON
  - every id in figure-map is referenced in the body (![...](img-NNN)) and
    vice versa -- no orphans in either direction
  - every figure-map entry has the required keys
  - if --manifest is given: every referenced id actually exists in the
    manifest, and references_manifest_caption matches the manifest's own
    caption verbatim
  - no Hugo-style {{< ... >}} / {{% ... %}} shortcode syntax anywhere
  - the NO-MANIFEST fallback, if present, is used consistently (empty
    figure-map, no img- references in the body)
  - a rough CJK-density check on the prose, as a signal the file may have
    come out in English (or some other non-Chinese-majority language) by
    mistake

Usage:
    python verify_article.py path/to/article.md [--manifest path/to/image-manifest.json]

Exits non-zero if any ERROR-level finding is present. WARNING-level findings
are printed but don't affect the exit code.
"""
import argparse
import json
import re
import sys

IMG_REF_RE = re.compile(r"!\[[^\]]*\]\((img-[0-9]+)\)")
HUGO_SHORTCODE_RE = re.compile(r"\{\{[%<].*?[%>]\}\}", re.DOTALL)
FIGURE_MAP_RE = re.compile(r"```figure-map\s*\n(.*?)\n```", re.DOTALL)
NO_MANIFEST_LINE = "<!-- NO-MANIFEST: figures referenced descriptively; Step 3 must match manually -->"
REQUIRED_KEYS = {"id", "references_manifest_caption", "why_used", "agent_match_hint"}
CJK_RE = re.compile(r"[一-鿿]")
VISIBLE_CHAR_RE = re.compile(r"\S")


def load_manifest_ids_and_captions(path):
    with open(path, encoding="utf-8") as f:
        manifest = json.load(f)
    return {img["id"]: img.get("caption") for img in manifest.get("images", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article", help="Path to article.md")
    ap.add_argument("--manifest", default=None, help="Path to image-manifest.json (omit for NO-MANIFEST articles)")
    args = ap.parse_args()

    with open(args.article, encoding="utf-8") as f:
        text = f.read()

    errors = []
    warnings = []

    no_manifest_mode = text.lstrip().startswith(NO_MANIFEST_LINE)

    body_ids = set(IMG_REF_RE.findall(text))

    fm_match = FIGURE_MAP_RE.search(text)
    if not fm_match:
        errors.append("No ```figure-map``` fenced block found (or it isn't the last thing in the file).")
        figure_map = []
    else:
        try:
            figure_map = json.loads(fm_match.group(1))
        except json.JSONDecodeError as e:
            errors.append(f"figure-map block is not valid JSON: {e}")
            figure_map = []
        if not isinstance(figure_map, list):
            errors.append("figure-map block must be a JSON array.")
            figure_map = []

    fm_ids = set()
    for i, entry in enumerate(figure_map):
        if not isinstance(entry, dict):
            errors.append(f"figure-map[{i}] is not a JSON object.")
            continue
        missing = REQUIRED_KEYS - set(entry.keys())
        if missing:
            errors.append(f"figure-map[{i}] (id={entry.get('id', '?')}) missing keys: {missing}")
        eid = entry.get("id")
        if eid:
            if eid in fm_ids:
                errors.append(f"duplicate id in figure-map: {eid}")
            fm_ids.add(eid)

    if no_manifest_mode:
        if fm_ids or body_ids:
            errors.append(
                "File starts with the NO-MANIFEST comment, but figure-map/body still reference "
                f"manifest ids (figure-map: {fm_ids or 'none'}, body: {body_ids or 'none'}). "
                "NO-MANIFEST articles must reference figures descriptively in prose only, with an "
                "empty figure-map."
            )
    else:
        orphan_body = body_ids - fm_ids
        orphan_fm = fm_ids - body_ids
        if orphan_body:
            errors.append(f"Body references ids missing from figure-map: {sorted(orphan_body)}")
        if orphan_fm:
            errors.append(f"figure-map has ids never referenced in the body: {sorted(orphan_fm)}")

    if HUGO_SHORTCODE_RE.search(text):
        errors.append("Found Hugo-style {{< ... >}} / {{% ... %}} shortcode syntax -- that belongs in Step 3's Hugo repo, not here.")

    if args.manifest:
        manifest_captions = load_manifest_ids_and_captions(args.manifest)
        for entry in figure_map:
            if not isinstance(entry, dict):
                continue
            eid = entry.get("id")
            if eid is None:
                continue
            if eid not in manifest_captions:
                errors.append(f"figure-map id {eid!r} does not exist in the manifest -- never invent an id.")
                continue
            manifest_caption = manifest_captions[eid]
            claimed = entry.get("references_manifest_caption")
            if manifest_caption is not None and claimed != manifest_caption:
                errors.append(
                    f"{eid}: references_manifest_caption doesn't match the manifest's caption verbatim "
                    "(it must copy the manifest field exactly, untranslated, for Step 3's join to work)."
                )
    elif not no_manifest_mode and fm_ids:
        warnings.append("No --manifest given -- skipped cross-checking figure-map ids/captions against the manifest.")

    # Rough CJK-density check on the prose, excluding the figure-map block itself.
    prose = text[: fm_match.start()] if fm_match else text
    visible = VISIBLE_CHAR_RE.findall(prose)
    cjk = CJK_RE.findall(prose)
    if len(visible) > 200:  # skip the check on trivially short files
        ratio = len(cjk) / len(visible)
        if ratio < 0.3:
            warnings.append(
                f"Only {ratio:.0%} of visible characters in the prose are CJK -- this article is "
                "supposed to be written in Traditional Chinese (Taiwan usage). Double-check it didn't "
                "come out in English."
            )

    for w in warnings:
        print("WARNING:", w)
    if errors:
        print("\nERRORS:", file=sys.stderr)
        for e in errors:
            print(" -", e, file=sys.stderr)
        sys.exit(1)
    print("All checks passed.")


if __name__ == "__main__":
    main()
