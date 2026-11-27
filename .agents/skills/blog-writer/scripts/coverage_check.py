#!/usr/bin/env python3
"""
List notes content that never made it into article.md: numbers (with their
%/M/B/K/× unit) and Latin-script terms (method names, benchmarks, code
identifiers), grouped by the notes heading they sit under, with line numbers.

A candidate list for the Writer and Reviewer B, not a verdict. It reports
generously on purpose: a number reworded on purpose ("1B" written as
"10 億") shows up here too, and someone has to decide. Every item the Writer
leaves out on purpose needs a one-line reason in the delta file, and that
list goes in the PR Notes.

Skipped: integers below 10 with no unit (list ordinals, counts like "3 次"),
the notes' own heading lines, code fences, and quoted English passages
(「...」 spans that are mostly ASCII, such as a pasted original caption).

Usage:
    python coverage_check.py <notes.md> <article.md> [--skip-heading REGEX ...]
"""
import argparse
import html
import re
import sys

NUM_RE = re.compile(r"(?<![\w.])[−\-+]?\d+(?:[.,]\d+)*\s?(?:%|×|[MBK](?![A-Za-z]))?")
TERM_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_\-\.→]*[A-Za-z0-9]")
FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
QUOTE_RE = re.compile(r"「([^」]*)」")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def norm_num(s):
    s = s.replace("−", "-").replace(" ", "")
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
    s = re.sub(r"(\.\d*?)0+(?=\D|$)", r"\1", s)  # 0.50 -> 0.5
    s = re.sub(r"\.(?=\D|$)", "", s)                # 4. -> 4
    return s.lstrip("+")


def unescape(text):
    """Markdown backslash escapes and HTML entities, as notes exports carry them."""
    return html.unescape(re.sub(r"\\([\\`*_{}\[\]()#+\-.!|])", r"\1", text))


def strip_quotes(line):
    def repl(m):
        body = m.group(1)
        ascii_share = sum(c.isascii() for c in body) / max(1, len(body))
        return "「」" if ascii_share > 0.5 else m.group(0)
    return QUOTE_RE.sub(repl, line)


def number_tokens(text):
    out = []
    for m in NUM_RE.finditer(text):
        tok = norm_num(m.group(0))
        digits = re.sub(r"[^\d.]", "", tok)
        has_unit = tok[-1:] in "%×MBK"
        if not has_unit and "." not in digits and digits.isdigit() and int(digits) < 10:
            continue
        out.append(tok)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes")
    ap.add_argument("article")
    ap.add_argument("--skip-heading", action="append", default=[],
                    help="Regex; notes sections whose heading matches are skipped (e.g. an index)")
    args = ap.parse_args()

    with open(args.article, encoding="utf-8") as f:
        article = unescape(f.read())
    article = article.split("```figure-map")[0]
    art_nums = set(number_tokens(article))
    art_nums |= {re.sub(r"[%×MBK]$", "", n) for n in art_nums}
    art_terms = {t.lower() for t in TERM_RE.findall(article)}

    with open(args.notes, encoding="utf-8") as f:
        notes = unescape(f.read())
    notes = FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), notes)

    skip = [re.compile(p) for p in args.skip_heading]
    heading, skipping = "(before first heading)", False
    missing = {}
    seen = set()
    for lineno, line in enumerate(notes.split("\n"), start=1):
        h = HEADING_RE.match(line)
        if h:
            heading = h.group(2).strip()
            skipping = any(p.search(heading) for p in skip)
            continue
        if skipping:
            continue
        line = strip_quotes(line)
        for tok in number_tokens(line):
            if tok not in art_nums and re.sub(r"[%×MBK]$", "", tok) not in art_nums and ("n", tok) not in seen:
                seen.add(("n", tok))
                missing.setdefault(heading, []).append((lineno, "number", tok))
        for term in TERM_RE.findall(line):
            if len(term) < 3 or term.lower() in art_terms or ("t", term.lower()) in seen:
                continue
            seen.add(("t", term.lower()))
            missing.setdefault(heading, []).append((lineno, "term", term))

    total = sum(len(v) for v in missing.values())
    if not total:
        print("Coverage: every number and term in the notes appears in the article.")
        return
    print(f"Coverage: {total} notes item(s) not found in the article (candidates, not verdicts).\n")
    for heading, items in missing.items():
        print(f"## {heading}")
        for lineno, kind, tok in items:
            print(f"  line {lineno}: {kind} {tok}")
    sys.exit(0)


if __name__ == "__main__":
    main()
