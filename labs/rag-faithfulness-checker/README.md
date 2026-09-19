# RAG Faithfulness Checker — how to run it

Tests whether a model stays honest: does it answer **only** from the passage you
give it, or does it confidently make things up when the answer isn't there?

It compares two prompts — a **lax** grounding instruction vs a **strict** one —
over 4 cases, two of which are "traps" whose answer is NOT in the passage.

Runs exactly like the CoT experiment.

## Run it

1. Put this file and `promptfooconfig.yaml` in their own folder (e.g. `rag-faithfulness`).
2. Add a `.env` file in that folder with your key:
   ```
   OPENAI_API_KEY=sk-...your key...
   ```
3. From inside the folder:
   ```bash
   npx promptfoo@latest eval
   npx promptfoo@latest view
   ```

## What you're looking for

- **Cases 1 and 4** (answerable): both prompts should pass — the info is in the passage.
- **Cases 2 and 3** (traps — answer NOT in the passage): this is the whole point.
  - **lax** prompt: often **red** — it invents a plausible answer (a free trial, a weight).
  - **strict** prompt: **green** — it refuses and says the context doesn't say.

That contrast is the lesson: the *prompt*, not the model, decided whether the
system hallucinated. Faithfulness is something you engineer.

## Notes

- Grading uses `llm-rubric` (a second model judges each answer against a plain-language
  standard), so results are slightly stochastic — re-run to see stability.
- Add more models under `providers:` if you want to see whether bigger models
  hallucinate less even with the lax prompt.
