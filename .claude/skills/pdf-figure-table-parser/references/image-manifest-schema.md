# image-manifest.json schema

What `build_manifest.py` writes. Step 2 (`blog-writer`) and Step 3 (the Hugo
repo) both consume it; see the repo `CLAUDE.md` for the pipeline.

```json
{
  "source_pdf": "in-progress/<Topic>/<paper>.pdf",
  "generated_by": "pdf-figure-table-parser skill (pymupdf caption-anchored region render)",
  "images": [
    {
      "id": "img-001",
      "file": "in-progress/<Topic>/assets/images/picture-001.png",
      "type": "figure",
      "page": 5,
      "caption": "Figure 3: End-to-end latency vs. batch size across the three schedulers.",
      "nearby_text": "As shown in Figure 3, the proposed scheduler ...",
      "parser_confidence": "high"
    }
  ]
}
```

- **`id`**: sequential in reading order (`img-001`, ...); the join key
  downstream. Never reuse or renumber.
- **`file`**, **`source_pdf`**: repo-relative paths against the bucket the
  topic sat in when the parser ran. They go stale when the directory moves
  buckets, so every move rewrites them (repo `CLAUDE.md`, "Moving a topic
  between buckets"). The `picture-NNN.png` filename carries no meaning; use
  `caption`, never the filename, to tell which figure it is.
- **`type`**: `"figure"` | `"table"` | `"diagram"` | `"other"`. The builder
  derives it from whether the caption said "Figure" or "Table".
- **`page`**: 1-indexed source page, always filled in.
- **`caption`**: the caption text verbatim, never synthesized. A visual with
  no detected caption is not in the manifest at all.
- **`nearby_text`**: a body-text snippet elsewhere in the document that
  mentions the same "Figure N"/"Table N", for disambiguation. `null` if only
  the caption itself mentions it.
- **`parser_confidence`**: `"high"` | `"low"`. Figures are `high`; tables are
  `low` unless `table_markdown` was populated. Any entry that failed the crop
  geometry checks (`crop_warnings`: a near-empty region, or a figure crop that
  is mostly body prose) is forced to `low`, with a `SUSPECT CROPS` block naming
  it. When in doubt, `low`: downstream spot-checks `low` entries rather than
  trusting the manifest blindly.
- **`table_markdown`** (optional, tables only): present only when
  `pdfplumber` produced a clean, consistent-column table. Absent is normal (many
  tables have no ruling lines); the image is then the source of truth.
