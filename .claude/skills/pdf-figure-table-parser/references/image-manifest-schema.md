# image-manifest.json schema

This is the schema `build_manifest.py` writes. It matches what this repo's
blog-writing pipeline expects (see the repo's `CLAUDE.md` for the pipeline
overview) — Step 1 (`blog-writer`) reads a manifest built with this skill
directly, and Step 3 (in the separate Hugo repo) consumes it too. If you're
using this skill outside that pipeline, treat this as a sensible default you
can adapt.

```json
{
  "source_pdf": "docs/<slug>/source.pdf",
  "generated_by": "pdf-figure-table-parser skill (pymupdf caption-anchored region render)",
  "images": [
    {
      "id": "img-001",
      "file": "docs/<slug>/assets/images/picture-001.png",
      "type": "figure",
      "page": 5,
      "caption": "Figure 3: End-to-end latency vs. batch size across the three schedulers.",
      "nearby_text": "As shown in Figure 3, the proposed scheduler ...",
      "parser_confidence": "high"
    }
  ]
}
```

Field notes:

- **`id`**: stable, sequential in reading order (`img-001`, `img-002`, ...).
  This is the join key downstream consumers use. Never reuse or renumber.
- **`file`**: repo-relative path to the rendered PNG. The filename is
  neutral (`picture-NNN.png`) and carries no semantic meaning by design --
  never infer "this is Figure 3" from a filename; use `caption` instead.
- **`type`**: `"figure"` | `"table"` | `"diagram"` | `"other"`.
  `build_manifest.py` derives this directly from whether the caption said
  "Figure" or "Table" — good enough in practice, since diagrams are
  virtually always captioned as figures in academic papers.
- **`page`**: 1-indexed source page. `build_manifest.py` always fills this in
  (pymupdf reports it directly), so `null` should not occur in practice.
- **`caption`**: the caption text verbatim, exactly as extracted. Never
  synthesized -- a fabricated caption would corrupt any downstream matching
  against this manifest. If no caption block was found for a visual, it
  won't appear in the manifest at all (this pipeline only extracts visuals
  it can positively identify via a caption; see SKILL.md's limitations).
- **`nearby_text`**: a snippet of body text elsewhere in the document that
  references the same "Figure N" / "Table N" label, for downstream
  disambiguation. `null` if no such reference exists outside the caption
  itself (this does happen -- some figures are only ever referenced by
  their caption).
- **`parser_confidence`**: `"high"` | `"low"`. `build_manifest.py` marks
  figures `high` (region-render crops anchored precisely on caption/paragraph
  boundaries are reliable for born-digital PDFs) and tables `low` unless
  `table_markdown` was successfully populated. When in doubt, `low` is the
  safe choice -- a downstream step's job is to spot-check `low` entries, not
  to blindly trust the manifest.
- **`table_markdown`** (optional, tables only): present only when
  `pdfplumber`'s structured extraction produced a clean, consistent-column
  table. Many academic tables have no ruling lines at all, in which case
  this key is simply absent and the table's image is the source of truth --
  that is expected, not a bug.
