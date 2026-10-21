# Image reference convention + figure-map schema

The authoritative spec for how `article.md` refers to visuals.

The Writer doesn't know final image paths (Step 3 decides them in the Hugo
repo) and must never embed a parser filename like `picture-003.png`. The body
references the manifest `id`; a machine-readable block at the end gives Step 3
everything it needs to do the real match. The Reviewer reads only the body.

## In the article body

```markdown
![延遲會隨批次大小次線性成長，這是這個排程器的關鍵優勢。](img-001)
*圖 3 — 延遲與批次大小的關係。（來源：原始論文 Figure 3。）*
```

- **alt** (inside `![]`): Writer-authored Traditional Chinese describing what
  the visual shows, not "圖 3 的圖片".
- **src**: the manifest `id`, not a path. Step 3 rewrites it.
- **Italic caption line**: Writer-authored Traditional Chinese, not a copy of
  the manifest's English caption.

### Numbering

Number the visible captions (`圖 3 —`, `表 1 —`) **sequentially in the
article's own order, from 1, counting figures and tables separately.** Don't
carry the paper's numbers over: only visuals that earn a place are included, so
the paper's numbers have gaps, and a reader who can't see the paper concludes
a figure is missing. Step 3 joins on the manifest `id`, never on the label.

The paper's own number appears in exactly two places: the caption's source note
(`（來源：原始論文 Table 9。）`) and, where the prose must name the original, as
`論文 Table 9`. Everywhere else, prose points at embedded visuals by the
article's label (`表 4`). Mixing the two schemes in prose is a real review
finding: a reader sees "Table 9" and "表 9" and can't tell which is meant.
`verify_article.py` warns on both a non-sequential caption number and a bare
`Table N`/`Figure N` in prose.

## At the end of article.md

A single ```` ```figure-map ```` fenced block, valid JSON, one entry per
referenced id and no others:

````markdown
```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 3: End-to-end latency vs. batch size across the three schedulers.",
    "why_used": "支撐説明批次處理為何對這個排程器有幫助的段落。",
    "agent_match_hint": "一張延遲對批次大小的折線圖，圖中有三條線。"
  }
]
```
````

- **`id`**: the manifest's own id, matching the body `src`. Never invent or
  renumber.
- **`references_manifest_caption`**: a verbatim copy of the manifest `caption`
  for that id, **untranslated** (normally English), so Step 3 can confirm the
  join even if ids drift.
- **`why_used`**: your commentary on why this visual is here, in Traditional
  Chinese.
- **`agent_match_hint`**: a short visual description for Step 3's fallback
  disambiguation, in Traditional Chinese.

## Validation

Every `figure-map` id must also appear as `![...](img-NNN)` in the body and
vice versa, and must exist in the manifest. `scripts/verify_article.py`
checks all of this.
