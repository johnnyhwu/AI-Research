# Voice guide: 台灣繁體中文，讀起來像工程師寫的，不像 AI 生成的

This file is the concrete "how" behind `SKILL.md`'s hard rules #2 and #3.
Read it before drafting, not after — style is much easier to get right from
the first sentence than to retrofit into a finished English-shaped draft.

**Write directly in Chinese. Don't draft in English and translate.**
Translating a fully-formed English draft tends to drag English sentence
rhythm and idiom along with it, even when every individual word is correctly
translated. Think through the narrative arc, then write each section in
Chinese from the start.

## Terminology: use Taiwan usage, not PRC usage

The paper and any manifest captions will be in English technical terms —
that's fine, translate them using the term a Taiwanese engineer would
actually reach for. Some common mismatches to watch for (left = avoid /
PRC usage, right = use / Taiwan usage):

| Avoid | Use |
|---|---|
| 软件 | 軟體 |
| 硬件 | 硬體 |
| 程序 (code/program) | 程式 |
| 数据 | 資料 |
| 算法 | 演算法 |
| 用户 | 使用者 |
| 服务器 | 伺服器 |
| 网络 | 網路 |
| 内存 | 記憶體 |
| 缓存 | 快取 |
| 队列 | 佇列 |
| 带宽 | 頻寬 |
| 质量 (quality) | 品質 |
| 信息 (information) | 資訊 |
| 视频 | 影片 |
| 文件 (as in "file") | 檔案 |
| 默认 | 預設 |
| 优化 | 優化 (same char, but double-check simplified variants didn't slip in) |

More generally: if a term feels like it came out of a Simplified-Chinese
technical doc or a mainland tech blog, look for the Taiwan-community
equivalent instead (iThome, Medium 上的中文技術文章、Taiwan engineering blogs
are the right register to imitate).

Also use full-width Chinese punctuation throughout Chinese prose
(，。「」『』？！), not half-width English punctuation dropped into Chinese
sentences.

## Sentence and paragraph rhythm

AI-generated Chinese technical writing has a fairly recognizable set of
tics. Avoid these specifically:

- **Uniform medium-length sentences, one after another.** Real writing has
  rhythm — short sentences to land a point, longer ones to walk through a
  mechanism. Vary it. If you notice five sentences in a row all clocking in
  around 20-30 characters with a comma in the middle, break the pattern.
- **Overusing the Chinese em-dash (——) as a universal parenthetical glue.**
  It's fine occasionally, but leaning on it in nearly every paragraph reads
  as a stylistic tic, not a choice. Use 括號、冒號、句號分句, or just start a
  new sentence instead.
- **Formulaic enumeration transitions**: "首先...其次...再者...最後..." or
  "第一點...第二點..." used to structure prose paragraphs (not an actual
  list). Fine for an actual itemized list; overused as connective tissue in
  running prose, it reads mechanical.
- **Empty transition/hedge phrases** used as filler rather than because they
  add information: "值得注意的是"、"毫無疑問"、"眾所周知"、"不可否認"、"總而言之"
  at the start of paragraph after paragraph. If the sentence works with the
  phrase deleted, delete it.
- **Restating the same point twice in a row** ("這意味著 X。換句話說，X。").
  Say it once, well.
- **Bolding too many phrases.** Reserve **bold** for a term's first
  introduction or a genuinely load-bearing point — not a scattering of
  emphasis across every paragraph, which is a very recognizable LLM tic in
  Chinese output.
- **Tour-guide narration**: "讓我們一起來看看"、"接下來我們將深入探討",
  addressing the reader as if hosting a webinar. A technical blog post
  states things; it doesn't announce that it's about to state things.

## Structural readability (beyond voice)

Correct, well-voiced prose can still be hard to follow if it's structured
poorly. These are mechanical, checkable rules — distinct from the voice tics
above, and just as often the actual cause when a reader says "the content is
right but I had trouble reading it":

- **One idea per paragraph, 2-3 sentences, lead with the point.** Put the
  paragraph's main claim in its first sentence, not buried at the end after
  three sentences of wind-up. If a paragraph is doing two things, split it.
  As a rough ceiling, a paragraph that runs past ~150 字 (full-width
  characters) is usually trying to do too much — that's a sign to split it,
  not evidence the section is "thorough."
- **Don't let the opening stall.** Get to the actual substance quickly — a
  long lead-in before the first concrete claim reads as padding, not as
  scene-setting.
- **When a term/abbreviation resurfaces much later, re-anchor it briefly.**
  If you defined an acronym or a named concept early on and it reappears
  several paragraphs later, don't assume the reader still holds it in
  working memory — a short parenthetical reminder ("...（也就是前面提到的
  XXX）...") costs one clause and saves the reader from scrolling back up.
  You don't need to re-explain it in full, just re-anchor it.
- **Every abstract mechanism needs one concrete example or scenario.**
  "這個方法能讓模型更有效率" on its own tells a first-time reader nothing they
  can hold onto. Follow any abstract claim about what a method *does* with a
  concrete case: a number, a before/after, or a situation an engineer would
  recognize. This is the same instinct as this repo's "target reader has
  never read the paper" rule (see `SKILL.md`), applied at the paragraph
  level instead of the whole-article level.
- **A/B comparisons belong in a table or clearly parallel bullets, not
  buried in a paragraph of running prose.** If you're contrasting two
  methods/settings across more than one dimension, lay it out so the reader
  can scan the contrast instead of reconstructing it from sentences.

## What natural Taiwanese engineer voice sounds like instead

- Direct, slightly conversational, but still precise — closer to a senior
  engineer explaining something to a colleague over the wiki than a
  press release. Occasional colloquial framing is good in small doses:
  "說白了"、"白話一點來說"、"老實說"、"這裡的眉角是"、"踩雷"、"接地氣" — but
  don't overdo it into slang-heavy or meme-heavy writing; this is a
  technical blog post, not a social media caption. One or two such phrases
  per article is plenty.
- State a claim, then immediately ground it in something concrete (a
  number, a mechanism, a specific example) rather than layering abstract
  qualifiers on top of each other.
- It's fine — good, even — to frame a section around a problem an engineer
  has actually hit ("如果你曾經手動調過 prompt，應該對這個場景不陌生：..."), but
  use this kind of hook once or twice in an article, not as a template
  repeated at the top of every section.
- Confident, plainspoken about limitations: "這裡有個很現實的限制" reads more
  natural than a hedgy "值得注意的是，這可能存在某些潛在的限制".

## Self-check before finishing a draft

- Read a paragraph out loud (mentally). Does it sound like something a
  person would actually say to a colleague, or does it sound like a
  well-formed but characterless summary?
- Scan for the tics listed above — em-dash density, formulaic enumeration,
  filler transition phrases, over-bolding. If a paragraph has more than one
  of these, rewrite it.
- Check terminology against the table above, especially for the most
  common nouns in the piece (they'll repeat many times, so a wrong term
  compounds).
- This is also exactly the kind of thing to ask the Reviewer subagent to
  flag (see `SKILL.md` workflow step 4) — its instructions already ask it
  to call out anything that reads as stiff/AI-translated Chinese.
