Every engineer building on top of a frozen, API-only LLM eventually runs into
the same wall: the model can't be fine-tuned for the task at hand, but its
default behavior isn't quite right either. It writes SQL that ignores a
schema quirk, forgets to check for an edge case, or picks the wrong tool for
a job it's done wrong ten times before. The usual fix is a hand-written
system prompt or "skill" document — a page of instructions prepended to
every call. The problem is that these documents are almost always
hand-tuned once and never touched again, or "improved" through a loop where
the model reflects on its last failure and rewrites the prompt on the spot.
That second approach sounds appealing, but in practice it tends to overfit
to whatever went wrong most recently, bloats the prompt with one-off patches,
and can quietly erase earlier lessons — a kind of catastrophic forgetting,
except happening in plain text instead of weights.

**SkillOpt**, a recent paper from Microsoft, reframes this problem instead of
trying to patch around it. Its core move is to stop treating prompt editing
as an ad hoc, unconstrained rewrite, and instead treat a skill document the
same way a deep learning optimizer treats a weight tensor: as external,
versioned, trainable state — something that gets updated in controlled,
bounded steps, validated before being kept, and rolled back when it doesn't
help. Nothing about the target model changes. All of the "learning" happens
in a text file.

## Two models, two jobs

SkillOpt splits responsibility between two separate models instead of asking
one model to both do the task and grade its own homework.

The **target model** ($M$) is the one actually doing the work — answering
questions, calling tools, writing code — inside whatever execution
environment the task requires (a plain chat harness, or something more
elaborate like Codex or Claude Code operating in a real workspace). Its
weights and its native system prompt are frozen throughout training. The
only thing that changes for it, run over run, is the skill document $s$
that gets prepended or dropped into its workspace. Formally, given a task
$x$ and skill $s$, the target model produces a trajectory and a scalar score
between 0 and 1: $(\tau(s), r(s)) = h(M, x, s)$.

The **optimizer model** ($O$) never touches the task itself. It's typically
a stronger "frontier" model, and it only runs offline, during training. Its
job is to read the target model's trajectories and scores and propose
concrete edits to the skill document — add this heuristic, delete that
stale instruction, replace this ambiguous phrasing.

Separating these two roles is what makes the deployed cost of this whole
setup effectively zero: once training finishes, all the optimizer-side API
spend disappears, and the only thing shipped to production is the frozen
target model plus a small text file.

## The skill file itself

That text file, called `best_skill.md`, typically ends up somewhere between
300 and 2,000 tokens. Depending on the harness, it's either prepended to the
system prompt directly (for a plain question-answering task) or written into
the target model's workspace as a persistent, on-disk note (for a tool-using
agent in something like Codex or Claude Code). Its contents are exactly
what you'd expect from a well-written internal runbook: general operating
procedures, domain-specific heuristics, tool-calling conventions, output
formatting rules, and defensive notes about known failure modes.

## Guarding against the model grading its own test

The single most important piece of engineering discipline in SkillOpt is
data isolation, borrowed directly from standard ML practice: a training
split ($D_{tr}$), a selection/validation split ($D_{sel}$), and a held-out
test split ($D_{test}$).

The optimizer model only ever sees trajectories from $D_{tr}$ — that's where
it gets its evidence for what to change. But it never sees $D_{sel}$ at all.
Every candidate skill produced during training has to be scored
independently against $D_{sel}$, and the rule for accepting it is strict:
the new skill's average score must be *strictly greater* than the current
skill's score. A tie doesn't count. This "strictly greater" bar closes off
the most common failure mode of iterative prompt editing — a string of
individually-plausible edits that, cumulatively, just add noise or bloat
without measurably helping.

![Overview of SkillOpt: a target model executes tasks with the current skill, an optimizer model turns the resulting trajectories into bounded edits, and a held-out validation gate accepts only the edits that measurably improve validation performance.](img-001)
*Figure 1 — Overview of SkillOpt. Accepted edits get folded into the deployed skill file; rejected edits become negative feedback fed into later steps. (Source: original paper.)*

The mental model the paper leans on throughout — and the one that makes the
rest of the design fall into place — is a direct analogy to classic deep
learning optimizers:

| Deep learning component | SkillOpt's text-space equivalent |
| --- | --- |
| Parameter ($W$) | The skill document (`best_skill.md`) |
| Gradient | Minibatch-derived edit proposals |
| Learning rate | Edit budget ($L_t$) |
| Validation checkpointing | The $D_{sel}$ blind gate with strict rejection |
| Momentum / EMA | Epoch-wise "slow update" |

Every mechanism described below exists to make one side of that table
actually work in text instead of in gradient space.

## Collecting evidence before touching anything

Each training step starts with a **rollout**: the target model runs the
current skill against a batch of 40 tasks drawn from $D_{tr}$. That's a
deliberately large batch. If you let the optimizer react to a single failed
trajectory, it tends to overfit to whatever specific noise caused that one
failure — a flaky network call, an unusually worded input — rather than
spotting a pattern that actually recurs. Forty examples give enough
statistical weight to distinguish a systematic weakness from a one-off
fluke.

Once the 40 trajectories come back, they're split into a **failure pool**
and a **success pool** based on score. This separation matters because the
two pools call for different kinds of edits: the failure pool is mined for
corrective fixes (what's broken and how to patch it), while the success
pool is mined for reinforcement (what's already working, but isn't written
down anywhere yet, so it might not survive to the next rollout by luck
alone).

## Diagnosing in parallel, MapReduce-style

Feeding all of a pool's failures into a single optimizer call at once would
blow past useful context and risk exactly the kind of "lost-in-the-middle"
behavior that gets worse as prompts get longer. Instead, SkillOpt slices
each pool into minibatches of 8 and analyzes every minibatch with its own
parallel API call — a shape that maps neatly onto MapReduce: each minibatch
is analyzed independently (Map), and the resulting proposals get folded
together later (Reduce). The system supports up to 16 of these calls
running concurrently, so even a step with several dozen trajectories to
diagnose across both pools clears in one parallel round rather than a long
serial queue.

A minibatch size of 8 is itself a deliberate middle ground: a size of 1 just
reproduces the single-trajectory overfitting problem the whole batch design
was meant to avoid, while 8 is small enough to stay well within context but
large enough to force the model to notice which failure mode actually shows
up across multiple tasks rather than fixating on one.

Each parallel call follows a fixed contract. The failure-side analyst
(`analyst_error.md`) receives 8 failing trajectories plus the current skill,
and returns a JSON object naming the common failure patterns it found and a
`patch` — a small list of atomic edits (`append`, `insert_after`, `replace`,
`delete`), each anchored to an exact target string in the skill file. The
success-side analyst (`analyst_success.md`) does the mirror version:
looking for good habits the model is already exhibiting that the skill
document doesn't mention yet, while staying conservative about reinforcing
things that are already well covered.

## Merging without losing the plot

Once the parallel analysts return their proposals, SkillOpt has to collapse
potentially many overlapping, sometimes-contradictory edit lists into one.
It does this with a two-stage hierarchical merge.

First, if there are more than 8 proposals in either pool, they go through a
**tree-reduce**: batches of at most 8 get merged pairwise (via
`merge_failure.md` or `merge_success.md`) until only one unified list per
pool remains. During this merge, duplicate suggestions get collapsed into
the most general phrasing, with a `support_count` that tracks how many
independent analysts proposed something equivalent — a rough proxy for how
often that particular failure or good habit actually showed up. Proposals
that try to edit the exact same location in the skill file in incompatible
ways get resolved here too, rather than left to collide later.

Second, the two now-unified lists — one from the failure pool, one from the
success pool — go through a final cross-pool merge (`merge_final.md`), and
the rule here is unambiguous: **failure fixes always win**. If a success-pool
edit and a failure-pool edit target the same spot in the document, the
failure-pool version is kept, full stop, and only non-conflicting success
edits survive to the next stage. Fixing something broken is treated as
strictly higher priority than reinforcing something that already works.

![Full pipeline of SkillOpt: rollout, minibatch reflection, hierarchical merge, ranking under a budget, and a held-out validation gate, repeated across epochs with a slow/meta update layered on top.](img-002)
*Figure 2 — Pipeline of SkillOpt, showing how a rollout batch flows through minibatch reflection, merging, budget-constrained ranking, and validation before an edit is ever committed to disk. (Source: original paper.)*

## A learning rate for text: the edit budget

After merging, there might still be far more proposed edits than it's safe
to apply in one step. SkillOpt caps how many edits can land in a single
step with an **edit budget**, $L_t$ — the direct textual analogue of a
learning rate. Applying too many edits at once is exactly like taking too
large a gradient step: the skill document can lurch into an unstable
configuration and lose earlier, hard-won lessons.

The budget itself follows a cosine decay schedule, typically starting around
$L_t = 4$ and shrinking to $L_t = 2$ as training progresses. Early on, the
skill document is mostly empty, so bigger structural changes are safe and
useful (exploration). Later, once the document has accumulated real
content, only small wording-level tweaks should get through (consolidation)
— pushing more than that risks unraveling something that already works.

Deciding *which* edits make it into that budget is handled by a dedicated
ranking step (`ranking.md`), which sorts all merged candidates by four
criteria, strictly in this order of priority: how many trajectories a fix
would actually help (tied to `support_count`), whether it fills a real gap
rather than restating something already in the document, whether it reads
as a generally applicable rule rather than something hard-coded to one
task's quirks, and whether it's concrete and actionable rather than vague
advice. Only the top $L_t$ survive into the candidate skill.

## The gate that actually decides

The candidate skill produced by applying those edits, $\tilde{s}$, isn't
trusted just because it looks reasonable — it has to earn its way in by
being scored, blind, against $D_{sel}$, exactly the split the optimizer
never got to see. Only if $\text{score}(\tilde{s})$ is *strictly greater*
than the current skill's score does the candidate get written to disk and
become the new current skill. A tie or a drop means the whole step is
thrown away and the previous skill is kept unchanged.

Rejections aren't wasted, though. Whatever a rejected step tried to change,
along with the failure pattern it was chasing and how much the score
dropped, gets logged into a short-term **rejected-edit buffer**. That
history gets folded as context into the *next* step's analyst and ranking
calls, phrased roughly as "we already tried this and it hurt validation
performance — don't propose it again." It's a small mechanism, but it stops
the optimizer from cycling through the same bad idea step after step.

There's also a practical safety net for a much more mundane failure mode:
the optimizer's proposed edits are applied via exact string matching against
the skill document, and LLMs do occasionally hallucinate a target string
that doesn't actually appear verbatim. When that happens, that one edit is
simply marked `skip` in an `edit_apply_report.json` log rather than crashing
the pipeline, and every other, unaffected edit in the same batch still
applies normally.

## Zooming out at the end of every epoch

Step-by-step edits are myopic by design — each one only reacts to the most
recent batch of 40 tasks. To catch longer-horizon regressions, SkillOpt adds
a second, slower control loop that runs once per epoch instead of once per
step.

At the epoch boundary, the system pulls 20 tasks at random from the training
set and re-runs *both* the previous epoch's skill and the current epoch's
skill against that same fixed set — a controlled A/B comparison, not just a
raw score. Each of the 20 tasks then falls into one of four buckets:
improved, regressed, still failing, or still succeeding. The **regressions**
bucket is the one that matters most, since it's the clearest signal that
recent step-level edits, despite each individually passing its own
validation gate, have collectively made something worse.

A dedicated "slow update" call (`slow_update.md`) reads that comparison and
writes a macro-level strategic note, which gets inserted into
`best_skill.md` inside a specially marked, protected region delimited by
`<!-- SLOW_UPDATE_START -->` / `<!-- SLOW_UPDATE_END -->` comments. For the
rest of that epoch, ordinary step-level edits are locked out of touching
anything inside that region — only the epoch-boundary process can update
it. This is a direct textual stand-in for momentum or an exponential moving
average in ordinary optimizers: it captures a longer-horizon trend that
shouldn't get erased by short-term noise. Even this update isn't unconditionally
trusted, though — it still has to pass the same $D_{sel}$ gate, and gets
rolled back if it doesn't measurably help.

Alongside the slow update, there's a second, stranger mechanism: a **meta
skill**. This is a separate document, written by the optimizer for itself,
summarizing lessons about what kinds of edits tend to pass validation versus
get rejected in this particular domain. It never touches `best_skill.md` and
the target model never sees it at all — instead, it gets prepended to the
*optimizer's own* system prompt in the next epoch, so the coach gets better
at proposing edits over time, without the deployed skill file growing by a
single token. It's a small but clean instance of meta-learning: the
optimizer is learning how to optimize in this environment, entirely
separately from what gets deployed.

## Does any of this actually work?

The paper's headline result is a main comparison across six benchmarks,
several target model sizes (from GPT-5.5 down to a much smaller Qwen3.5-4B),
and three execution harnesses (direct chat, Codex, and Claude Code) — 52
(model, benchmark, harness) cells in total.

![Main results table: SkillOpt is the best-or-tied entry across all 52 measured (model, benchmark, harness) cells, with consistent positive gains over the no-skill baseline.](img-003)
*Table 1 — Main results on held-out test splits, comparing SkillOpt against a no-skill baseline and several other prompt-optimization baselines. (Source: original paper.)*

SkillOpt comes out best-or-tied on every single one of those 52 cells,
beating out baselines like TextGrad, GEPA, and EvoSkill throughout. The size
of the gain depends on the harness: roughly +23.5 points on average in plain
direct-chat settings, and a comparably large +24.8 points in the tool-using
Codex harness, with a still-substantial +19.1 points in Claude Code. The
Codex number is arguably the more interesting of the two: it suggests that a
lot of the available headroom in tool-using agents isn't in the underlying
model's raw capability at all, but in how well the surrounding operating
procedure is specified.

What makes those gains more credible than "we tuned really hard on the test
set" is how cheap the final artifact turns out to be, and how few edits it
actually took to get there.

![Cost and edit economy across six benchmarks: only 1 to 4 accepted edits per benchmark, with wide variance in the training-token cost required per point of improvement.](img-009)
*Table 6 — Cost and edit economy of the GPT-5.5/GPT-5.5 runs, showing final skill length, accepted edit counts, and training-token cost per absolute test-point gained. (Source: original paper.)*

Across all six benchmarks, the final skill files needed only **one to four
accepted edits** — the validation gate rejects the overwhelming majority of
proposed changes, which is exactly the kind of selectivity you'd want from a
system this cautious. Token cost per point of improvement, though, varies
enormously by task shape: benchmarks with short, tool-call-heavy trajectories
(SpreadsheetBench, OfficeQA) cost as little as 0.6–1.1M training tokens per
point gained, while long-context tasks (SearchQA, DocVQA) cost 38–46M tokens
per point — a real, practical planning input for anyone deciding whether
this is worth running on a given task.

The paper also pushes on whether what gets learned is genuinely general, or
just a memorized answer key for the exact tasks it trained on. The transfer
experiments are the strongest evidence for the former.

![Transfer results across three axes: cross-model, cross-harness, and cross-benchmark. Every transferred cell shows a positive gain over the target's own no-skill baseline.](img-006)
*Table 4 — Transfer of optimized skills across model scale, execution harness, and benchmark, with every transferred cell improving on the target's no-skill baseline. (Source: original paper.)*

The most striking single number here is a cross-harness transfer: a skill
trained inside Codex on a spreadsheet task, when dropped into Claude Code
without any further optimization, took that harness's score from 22.1 to
81.8 — a +59.7 point jump, and one that actually *exceeds* the score
achieved by training a skill directly inside Claude Code (80.4). That's a
strong hint that what the optimizer extracts is closer to "how to think
about manipulating spreadsheet data with Pandas" than "how to phrase
instructions for this specific harness's syntax." Across all three transfer
axes tested — model scale, harness, and benchmark — not a single
transferred cell fell below its target's own no-skill baseline.

Finally, the paper checks how much of this depends on having access to a
frontier-grade optimizer model in the first place.

![Effect of optimizer strength: even a weaker, target-matched optimizer recovers most of the gains achieved with a stronger frontier optimizer.](img-008)
*Table 5 — Effect of optimizer strength, comparing a strong frontier optimizer (GPT-5.5) against a target-matched optimizer that coaches itself, with everything else in the loop held fixed. (Source: original paper.)*

Even when the "coach" is downgraded to the same (much smaller) model as the
target — i.e., the target model optimizing itself — the bounded-update and
validation-gate machinery is enough to recover 56–74% of the gain seen with
a frontier-grade optimizer. That's a meaningfully practical result for teams
without frontier-model budget to spend on offline training: self-coaching
is degraded, but far from useless.

## Where the cracks show

It would be easy to read a 52/52 sweep and stop there, but the paper (and
the discussion this article is based on) is fairly upfront about where this
design is likely to strain in production.

The whole system leans entirely on the validation gate, and the gate leans
entirely on having a **cheap, reliable, automatic scorer**. For tasks with a
verifiable answer — code that either passes tests or doesn't, a spreadsheet
transformation that either matches the target or doesn't — that's a
reasonable assumption. For open-ended, subjective tasks (creative writing,
freeform customer support), building a scorer good enough to gate on
honestly may require an LLM-as-judge setup, which reintroduces exactly the
cost and noise this pipeline was trying to avoid in the first place.

The economics also cut both ways. Deployment cost is genuinely zero — no
extra inference, no extra latency, just a static text file — but getting
there requires tens to hundreds of millions of training tokens even for a
single skill, per Table 6 above. That tradeoff clearly favors **high-frequency,
structurally stable, high-cost-of-error** production agents (financial
report automation, ops runbooks) over one-off or low-frequency tasks, where
the token investment probably never pays back.

And structurally, the design deliberately keeps everything in a single
`best_skill.md` file to stay simple — which is exactly what will eventually
become the bottleneck for a large, heterogeneous deployment covering
hundreds of distinct business scenarios in one system. A single Markdown
file will hit context limits, and rules meant for different scenarios can
start actively contradicting each other inside the same document. The
natural next step, if this needs to scale that far, looks like pairing
SkillOpt with some kind of skill-library router — multiple domain-specific
skill files, each optimized independently, selected by a dispatcher at
runtime rather than crammed into one file.

## The takeaway

What SkillOpt is really arguing for is a shift in how prompt/skill iteration
gets treated: not as a black-box trial-and-error loop, but as an actual
optimization pipeline with the same discipline deep learning takes for
granted — batched evidence instead of single anecdotes, a bounded step size
instead of unconstrained rewrites, a genuinely blind validation split
instead of eyeballing whether an edit "seems like it helped," and a longer-
horizon mechanism to keep short-term patches from eroding earlier lessons.
None of it requires touching model weights, and none of it costs anything
extra once deployed — which is precisely why it's worth a serious look for
any team maintaining a frozen-model agent that keeps making the same kind
of mistake.

```figure-map
[
  {
    "id": "img-001",
    "references_manifest_caption": "Figure 1 Overview of SkillOpt. The target model executes tasks with a current skill, an additional frontier optimizer model converts trajectories into bounded add/delete/replace skill edits, and a held-out gate accepts only edits that improve validation performance. Accepted edits are exported as a reusable skill artifact, while rejected edits become negative feedback for later updates.",
    "why_used": "Introduces the overall SkillOpt loop right after the data-isolation/validation-gate explanation, giving the reader a schematic anchor before the article dives into the loop's individual stages.",
    "agent_match_hint": "A schematic/overview diagram showing a target model, an optimizer model, and a validation gate arranged as a loop, with accepted/rejected edit paths."
  },
  {
    "id": "img-002",
    "references_manifest_caption": "Figure 2 Pipeline of SkillOpt. A frozen target model executes a rollout batch with the current skill; an optimizer model performs minibatch reflection over successes and failures, proposes bounded add/delete/replace edits, merges and ranks them under a scheduled edit budget, and accepts the candidate skill only through a held-out validation gate. Across epochs, the slow/meta update retains longer-horizon lessons without changing the target model.",
    "why_used": "Placed right after the edit-budget/ranking explanation to give a single visual summary of the full step-level pipeline (rollout -> reflection -> merge -> rank -> gate) before the article moves on to epoch-level mechanisms.",
    "agent_match_hint": "A more detailed pipeline diagram with multiple stages/boxes: rollout batch, minibatch reflection, hierarchical merge, ranking under a budget, and a validation gate, plus an epoch-level slow/meta update loop."
  },
  {
    "id": "img-003",
    "references_manifest_caption": "Table 1 Main results on held-out test splits. Scores are percentages; within each model–harness block, bold marks the best measured entry and underlining marks the second-best entry for each benchmark. Blue cells denote SkillOpt, and small green/red subscripts show the absolute change relative to the No skill row of the same model in the same harness. We omit ALFWorld under Codex and Claude Code harnesses because ALFWorld requires persistent embodied-environment interaction. SkillOpt is the best-or-tied entry on every measured cell of the table, with positive gains over the no-skill baseline throughout.",
    "why_used": "Supports the headline results paragraph reporting SkillOpt's best-or-tied performance across all 52 (model, benchmark, harness) cells.",
    "agent_match_hint": "A large results matrix/table with models and harnesses as rows or column groups, benchmarks as columns, percentage scores, bold/underlined cells, and small colored subscript numbers."
  },
  {
    "id": "img-006",
    "references_manifest_caption": "Table 4 Transfer of optimized skills across three axes. (a) Cross-model: a skill optimized for the source model is deployed on the target model. (b) Cross-harness: a skill trained inside the source harness is evaluated inside the target harness, all on GPT–5.5. (c) Cross-benchmark: the source benchmark skill is evaluated on the target benchmark across three target models. Baseline is the target’s no-skill score, Direct is the in-domain SkillOpt score, and Transferred applies the source skill without further optimization. Subscripts show the change over the target baseline. The GPT–5.4→GPT–5.4 transferred cells in (a) are marked – because source and target match (i.e. no transfer occurs); we still report the GPT–5.4 baseline and in-domain SkillOpt score (taken from Table 1) in those rows for reference. Every remaining row in (a)–(c) is a positive transfer (no row falls below the target’s no-skill baseline).",
    "why_used": "Supports the discussion of the cross-model/cross-harness/cross-benchmark transfer experiments, especially the +59.7 point cross-harness result.",
    "agent_match_hint": "A table with three labeled sub-panels (a), (b), (c) for cross-model, cross-harness, and cross-benchmark transfer, each with baseline/direct/transferred score columns."
  },
  {
    "id": "img-007",
    "references_manifest_caption": "Figure 3 Performance trends across epoch checkpoints on three benchmarks: (a) SpreadsheetBench, (b) SearchQA, and (c) LiveMath. For each checkpoint, we report the training rollout score, the selection-best score on the validation set, and the final performance on the unseen test set. The results show how skill quality evolves during optimization and whether the checkpoint preferred by validation selection aligns with the checkpoint that yields the best generalization to the test set.",
    "why_used": "Referenced alongside the optimizer-strength discussion as supporting evidence that the validation-selected checkpoint tracks true test-set generalization rather than overfitting to the training rollouts.",
    "agent_match_hint": "A line chart (or set of three small line charts) with epoch/checkpoint on the x-axis and score on the y-axis, showing three lines: training rollout score, validation-best score, and test score."
  },
  {
    "id": "img-008",
    "references_manifest_caption": "Table 5 Effect of optimizer strength. Each (benchmark, target) pair is optimized either by a strong frontier optimizer (GPT–5.5, bolded) or by a target-matched optimizer that shares the target model; everything else in the SkillOpt loop is held fixed. Gains over the target’s no-skill baseline are shown as small green subscripts; the same baseline is used for both optimizer settings within a row. The optimizer runs only during offline training, so the stronger-optimizer column adds zero cost at deployment.",
    "why_used": "Supports the discussion of how much of SkillOpt's gain depends on having a frontier-grade optimizer, versus a target-matched (self-coaching) optimizer.",
    "agent_match_hint": "A table comparing a strong frontier optimizer column against a target-matched optimizer column for the same benchmarks, with subscript gain values."
  },
  {
    "id": "img-009",
    "references_manifest_caption": "Table 6 Cost and edit economy of the GPT–5.5 / GPT–5.5 (student / teacher) skill runs. Initial and final best_skill.md lengths are in tokens; Edits is the number of accepted bounded updates; Cost / pt is training tokens per absolute test-point gain. One representative learned rule per benchmark is shown in Figure 4.",
    "why_used": "Supports the discussion of how few edits (1-4) were needed per benchmark and the wide variance in training-token cost per point of improvement across benchmarks.",
    "agent_match_hint": "A table with one row per benchmark, columns for initial/final skill length in tokens, number of accepted edits, total training tokens, and cost per test-point gained."
  }
]
```
