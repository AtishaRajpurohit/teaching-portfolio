# ACE — Agentic Context Engineering

**Paper:** *Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models*
Qizheng Zhang, Changran Hu, Shubhangi Upasani, Boyuan Ma, Fenglu Hong, Vamsidhar Kamanuru,
Jay Rainton, Chen Wu, Mengmeng Ji, Hanchen Li, Urmish Thakker, James Zou, Kunle Olukotun.
arXiv:2510.04618 (6 Oct 2025). Code: [github.com/ace-agent/ace](https://github.com/ace-agent/ace)

---

## 1. The one-sentence version

Instead of updating a model's **weights** so it gets better at your task, update its
**context** — and let the model do that updating itself, as a structured, append-mostly
playbook that grows with experience.

## 2. Why this is a real problem

Everyone already does context adaptation: system prompts, few-shot examples, RAG,
"memory". The paper's contribution is naming *why the naive version degrades* and fixing it.

**Failure mode 1 — brevity bias.** Ask an LLM to "rewrite and improve this prompt" and it
optimises for something that reads well. Prompt optimisers drift toward short, elegant,
generic instructions. But an agent's real edge is often a pile of unglamorous specifics:
*this* endpoint 429s, *that* table is deprecated, amounts are in cents. Terse prompts throw
exactly that away.

**Failure mode 2 — context collapse.** If each update is "here is the whole context, please
rewrite it," the model is re-generating everything from scratch every round. Details silently
evaporate one monolithic rewrite at a time. The paper shows a context shrinking from ~18k
tokens to ~120 in a single step, with accuracy falling off a cliff alongside it.

Both failures share one root cause: **the whole context is rewritten as one blob.**

## 3. The fix: three roles, one playbook

ACE splits adaptation into a division of labour, which is where the "agentic" in the name
comes from — the context is maintained by agents, not by a human prompt-engineer.

| Role | Job | Analogy |
|---|---|---|
| **Generator** | Does the actual task. Produces the answer *and* a reasoning trace showing which strategies it leaned on. | The player |
| **Reflector** | Looks at the trace plus feedback (a test result, an error, a human correction, ground truth) and extracts *concrete, reusable lessons*. | The coach reviewing tape |
| **Curator** | Turns lessons into small structured **delta** operations against the playbook, and merges them in. | The editor of the team handbook |

The **Playbook** is not a prose paragraph. It is an itemised list, where each bullet has:

- a stable **id**,
- a **section** (grouping),
- the **content** — one specific, actionable strategy or fact,
- **helpful / harmful counters** tracking how it has performed when cited.

Two properties fall out of that structure, and they are the whole point:

**Incremental delta updates.** The Curator emits `ADD` / `UPDATE` / `REMOVE` on individual
bullets. Nothing else in the playbook is touched. Untouched knowledge is preserved *exactly*,
so collapse is structurally impossible rather than merely discouraged. It is also cheap —
you generate a handful of bullets, not a whole document — and it parallelises, since
non-overlapping deltas can be merged.

**Grow-and-refine.** Playbooks would otherwise bloat forever, so new bullets are
de-duplicated against existing ones (semantically, via embeddings) and low-value or
contradicted bullets get pruned. Detail is retained; redundancy is not.

Note what is *absent*: no labelled training set is required. The Reflector can work from
**natural execution feedback** — the code threw, the test failed, the API returned 404. On
AppWorld the paper reports up to a **+17.1%** gain from execution feedback alone.

## 4. What it buys you (reported results)

| Setting | Result |
|---|---|
| Agents (AppWorld) | **+10.6%** average over strong baselines |
| Domain reasoning (FiNER, Formula — financial/XBRL) | **+8.6%** average |
| AppWorld leaderboard | Matches the top-ranked production agent overall and **beats it on the harder test-challenge split** — using DeepSeek-V3.1, a smaller open-source model |
| Adaptation cost (offline, vs GEPA) | **−82.3%** latency, **−75.1%** rollouts |
| Adaptation cost (online, vs Dynamic Cheatsheet) | **−91.5%** latency, **−83.6%** token dollar cost |

The leaderboard line is the headline for a talk: a smaller open model with a good playbook
kept pace with a much larger model without one. Capability was not the bottleneck — context was.

## 5. How the demo maps onto the paper

The `ace-framework` package uses slightly different names than the paper. They line up
one-to-one:

| Paper | `ace` package | In `demo.py` |
|---|---|---|
| Generator | `Agent`, wrapped by `ACELiteLLM.ask()` | `learner.ask(question, context=...)` |
| Reflector | `Reflector` | invoked inside `learn_from_feedback()` |
| Curator | `SkillManager` | invoked inside `learn_from_feedback()` |
| Playbook | `Skillbook` (of `Skill` bullets) | `learner.skillbook`, saved to `ace_playbook.json` |
| Bullet / delta op | `Skill`, `UpdateOperation` | visible in `get_strategies()` |

So a single line —

```python
learner.learn_from_feedback(feedback=..., ground_truth=...)
```

— runs Reflector → Curator → `skillbook.apply_update(delta)`. That is the whole loop.

### The demo's setup

`house_rules.py` defines four facts about a fictional data warehouse that **no pretrained
model can possibly know**: an internal table name, an internal test-row flag, a storage unit
(cents), and a reporting timezone. That choice is deliberate — it isolates the variable.
A stronger model, more reasoning, or a longer prompt cannot recover this information.
Only being *told, and remembering*, can.

`demo.py` then runs four acts:

1. **Cold agent** answers a query. Fluent SQL, wrong on all four house rules.
2. **Two rounds of feedback.** After each, the playbook is printed so you can watch bullets
   accumulate rather than get overwritten. Round 2's feedback is generated from the grader
   at runtime, so the demo never claims the agent failed when it didn't. Watch the
   `helpful` counters on individual bullets tick up while other bullets are left untouched
   — that is a delta update, live.
3. **Held-out question** neither agent has seen, answered twice: once by a fresh agent with
   an empty playbook (the control) and once by a fresh agent loaded from the saved
   `ace_playbook.json`. Both are graded against the four rules.
4. **Scoreboard.**

Same model, same weights, same question. The only difference is a JSON file.

## 6. Honest limits — worth raising before your audience does

- **The Reflector is the ceiling.** The playbook can only be as good as the lessons
  extracted. Noisy or absent feedback yields noisy bullets, and a confidently wrong bullet
  is now *persistent* wrong.
- **Not everything needs it.** For tasks with no reusable structure across instances, an
  accumulated playbook is overhead.
- **Context length still costs money.** Grow-and-refine mitigates bloat but does not repeal
  it; a long playbook rides along in every request. (Prompt caching helps a lot here.)
- **It is complementary to fine-tuning, not a replacement.** ACE changes what the model
  *knows about your situation*; it does not change what the model is *capable of*.

## 7. Why it makes sense right now

Long contexts are cheap and getting cheaper, prompt caching makes a stable prefix nearly
free to re-send, and models have become good enough at self-critique for the Reflector step
to be trustworthy. ACE is a bet that the cheapest place to put new knowledge is no longer
the weights — it is a structured, versioned, human-readable text file sitting next to them.

That file is `ace_playbook.json`. Open it. That is the whole "training run", and you can
read it, diff it, review it in a PR, and delete a line you disagree with.
