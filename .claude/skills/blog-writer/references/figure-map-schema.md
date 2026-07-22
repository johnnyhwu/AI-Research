# Image reference convention + figure-map schema

This is the full version of the convention summarized in `SKILL.md`. There
is no more complete version elsewhere — treat this as the authoritative
spec, not a summary of some other document.

## Why the split exists

The Writer doesn't know final image paths — those are decided later by Step
3 in the separate Hugo repo — and must never embed a parser-native filename
(`picture-003.png` carries no meaning). Instead, the article references
visuals by the manifest's own `id`, and a machine-readable block at the end
gives Step 3 everything it needs to do the real match. This split is
deliberate: the Reviewer subagent reads the body as a naive reader and must
not be distracted by metadata, but Step 3 still gets a precise contract to
work from.

## In the article body

```markdown
![延遲會隨批次大小次線性成長，這是這個排程器的關鍵優勢。](img-001)
*圖 3 — 延遲與批次大小的關係。（來源：原始論文。）*
```

- The `alt` text (inside `![]`) is Writer-authored, in Traditional Chinese
  per this skill's hard rule, describing the visual's actual content — not
  "圖 3 的圖片" or similarly content-free.
- The `src` is the manifest `id` (`img-001`), **not** a file path. Step 3
  rewrites these to real Hugo paths later.
- The italic line under it is the visible, human-facing caption — also
  Writer-authored, in Traditional Chinese, not a copy-paste of the
  manifest's (usually English) caption field.

## At the end of article.md

A single fenced ```` ```figure-map ```` block, valid JSON, one entry per
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

Field notes:
- **`id`**: matches the `src` used in the body, and should be the manifest's
  own id directly (the Writer can see the manifest, so there's no reason to
  ever invent a new id or renumber).
- **`references_manifest_caption`**: a verbatim copy of the manifest's own
  `caption` field for that id — lets Step 3 confirm the join even if ids
  ever drift. **Keep this in whatever language the manifest caption is
  actually in** (normally English, since manifest captions are extracted
  straight from the source paper by Step 2) — do not translate this field,
  even though the rest of the article is in Traditional Chinese. Translating
  it would break the verbatim-match guarantee Step 3 relies on.
- **`why_used`**: Writer-authored explanation of why this visual was
  referenced here. Write this in Traditional Chinese, matching the rest of
  the article — it's your own commentary, not a copy of source text.
- **`agent_match_hint`**: a short visual description, used only as a
  fallback if Step 3 has to disambiguate or spot-check visually. Also
  Writer-authored — Traditional Chinese, same as `why_used`.

## Validation

Every id in `figure-map` must also appear as an `![...](img-NNN)` reference
somewhere in the body, and vice versa — no orphans in either direction. Every
id must exist in the manifest. `scripts/verify_article.py` checks all of
this automatically; run it before considering the article done.
