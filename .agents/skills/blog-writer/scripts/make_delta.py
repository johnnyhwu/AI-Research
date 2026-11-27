#!/usr/bin/env python3
"""
Write the delta file a resumed Reviewer reads instead of the whole article.

Diffs two versions of article.md paragraph by paragraph and writes, in order:

  1. a header saying whether a full re-read is needed instead (more than
     --reread-threshold of the paragraphs changed, or a ## section was added,
     removed or renamed);
  2. the Writer's per-finding responses (--responses, a file the Writer
     writes: "#3 fixed, see change C", "#9 kept, because ...", and for each
     deletion where that content now lives);
  3. the new version's heading outline;
  4. every change as: its heading path, the paragraph before, the removed
     paragraphs (`- `), the added paragraphs (`+ `), the paragraph after;
  5. verify_article.py output and, with --notes, coverage_check.py output.

The trailing figure-map block is left out of the diff.

Usage:
    python make_delta.py <old_article.md> <new_article.md> --out <delta.md>
        [--responses <responses.md>] [--manifest <image-manifest.json>]
        [--notes <notes.md> [--skip-heading REGEX ...]] [--reread-threshold 0.3]
"""
import argparse
import difflib
import os
import re
import subprocess
import sys

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
HERE = os.path.dirname(os.path.abspath(__file__))


def paragraphs(path):
    with open(path, encoding="utf-8") as f:
        text = f.read().split("```figure-map")[0]
    paras, current, fence = [], [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
        if not line.strip() and not fence:
            if current:
                paras.append("\n".join(current))
                current = []
        else:
            current.append(line)
    if current:
        paras.append("\n".join(current))
    return paras


def heading_path(paras, idx):
    """'## A > ### B' for the paragraph at idx."""
    stack = {}
    for p in paras[: idx + 1]:
        m = HEADING_RE.match(p.split("\n")[0])
        if m:
            level = len(m.group(1))
            stack = {k: v for k, v in stack.items() if k < level}
            stack[level] = f"{m.group(1)} {m.group(2)}"
    return " > ".join(stack[k] for k in sorted(stack) if k > 1) or "(top)"


def h2s(paras):
    return [p.split("\n")[0] for p in paras if re.match(r"^##\s", p)]


def quote(p, mark=""):
    return "\n".join(f"{mark}{line}" if mark else line for line in p.split("\n"))


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip() or "(no output)"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--out", required=True)
    ap.add_argument("--responses")
    ap.add_argument("--manifest")
    ap.add_argument("--notes")
    ap.add_argument("--skip-heading", action="append", default=[],
                    help="Passed through to coverage_check.py")
    ap.add_argument("--reread-threshold", type=float, default=0.3)
    args = ap.parse_args()

    old, new = paragraphs(args.old), paragraphs(args.new)
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    changed = sum(max(i2 - i1, j2 - j1) for _, i1, i2, j1, j2 in ops)
    share = changed / max(1, len(new))
    sections_changed = h2s(old) != h2s(new)

    out = ["# Review delta", ""]
    if share > args.reread_threshold or sections_changed:
        why = []
        if share > args.reread_threshold:
            why.append(f"{share:.0%} of paragraphs changed")
        if sections_changed:
            why.append("## sections were added, removed, renamed or reordered")
        out += [f"**FULL RE-READ NEEDED** ({'; '.join(why)}). Read the article itself: "
                f"`{os.path.abspath(args.new)}`. The changes below are still listed for reference.", ""]
    else:
        out += [f"{len(ops)} change(s), {share:.0%} of paragraphs. Review only what is below.", ""]

    out += ["## Writer responses to the last review", ""]
    if args.responses:
        with open(args.responses, encoding="utf-8") as f:
            out += [f.read().strip(), ""]
    else:
        out += ["(none given)", ""]

    out += ["## Outline of the new version", ""]
    out += [p.split("\n")[0] for p in new if HEADING_RE.match(p.split("\n")[0])] + [""]

    out += ["## Changes", ""]
    for n, (tag, i1, i2, j1, j2) in enumerate(ops):
        label = chr(ord("A") + n) if n < 26 else f"Z{n}"
        where = heading_path(new, max(0, min(j1, len(new) - 1)))
        out += [f"### Change {label} ({tag}) in {where}", ""]
        if j1 > 0:
            out += ["Before:", "", quote(new[j1 - 1], "> "), ""]
        if i2 > i1:
            out += ["Removed:", "", "\n\n".join(quote(p, "- ") for p in old[i1:i2]), ""]
        if j2 > j1:
            out += ["Added:", "", "\n\n".join(quote(p, "+ ") for p in new[j1:j2]), ""]
        if j2 < len(new):
            out += ["After:", "", quote(new[j2], "> "), ""]

    out += ["## Mechanical checks", "", "```"]
    verify = [sys.executable, os.path.join(HERE, "verify_article.py"), args.new]
    if args.manifest:
        verify += ["--manifest", args.manifest]
    out += [run(verify), "```", ""]
    if args.notes:
        cov = [sys.executable, os.path.join(HERE, "coverage_check.py"), args.notes, args.new]
        for h in args.skip_heading:
            cov += ["--skip-heading", h]
        out += ["```", run(cov),
                "```", ""]

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Wrote {args.out}: {len(ops)} change(s), {share:.0%} of paragraphs"
          + (", FULL RE-READ NEEDED" if share > args.reread_threshold or sections_changed else ""))


if __name__ == "__main__":
    main()
