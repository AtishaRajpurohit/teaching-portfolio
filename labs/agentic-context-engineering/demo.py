"""
ACE (Agentic Context Engineering) — live demo.

The story in one line: two identical agents, same model, same prompt. One of
them has been through two rounds of feedback and *wrote down what it learned*.
Watch the second one answer a question it has never seen.

Run:  uv run python demo.py
"""

import logging
import os
import sys
import textwrap
import time

from dotenv import load_dotenv

from house_rules import RULES, SCHEMA, applicable, grade

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# ACE and LiteLLM are chatty at INFO; the demo output is the point here.
logging.disable(logging.INFO)
os.environ.setdefault("LITELLM_LOG", "ERROR")

import litellm  # noqa: E402
litellm.suppress_debug_info = True

from ace import ACELiteLLM  # noqa: E402  (import after env is loaded)

MODEL = os.getenv("ACE_DEMO_MODEL", "anthropic/claude-sonnet-5")
SKILLBOOK_PATH = "ace_playbook.json"

# Claude Sonnet 5 / Opus 4.8 reject an explicit `temperature`. ACE drops the
# parameter entirely when it is None, which keeps the demo model-agnostic.
TEMPERATURE = None

# ---------------------------------------------------------------------------
# Terminal formatting
# ---------------------------------------------------------------------------

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, RED, CYAN, YELLOW = "\033[32m", "\033[31m", "\033[36m", "\033[33m"


def act(number: str, title: str) -> None:
    print(f"\n{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}  ACT {number}  —  {title}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}\n")


def step(text: str) -> None:
    print(f"{BOLD}{YELLOW}▸ {text}{RESET}")


def quote(text: str, color: str = DIM) -> None:
    for line in text.strip().splitlines():
        print(f"{color}   │ {line}{RESET}")
    print()


def pause(prompt: str = "press enter to continue") -> None:
    if os.getenv("ACE_DEMO_NOPAUSE"):
        return
    try:
        input(f"{DIM}   ({prompt}){RESET}")
    except EOFError:
        pass


# ---------------------------------------------------------------------------
# The task: write SQL against an internal warehouse
# ---------------------------------------------------------------------------

SYSTEM_CONTEXT = f"""\
You are a data analyst for an e-commerce company. Answer with a single
PostgreSQL query and one short sentence explaining it. Nothing else.

{SCHEMA}"""

TRAIN = [
    {
        "question": "What was our total revenue per day over the last 7 days?",
        "feedback": (
            "Wrong on four counts, and these are house rules that apply to every "
            "query you will ever write here — not just this one. (1) You used the "
            "`orders` table; it is a deprecated view that silently drops all "
            "marketplace channel rows. The live table is `fct_orders_v2` — same "
            "columns, plus an `is_test` flag. It is not in the data dictionary; "
            "nothing here is. (2) You did not exclude "
            "`is_test = TRUE` rows; our load tests write millions of fake orders "
            "straight into production, so every revenue or count query must filter "
            "them out. (3) `amount` is stored as an INTEGER number of cents, so a "
            "raw SUM(amount) reports 100x the real figure — divide by 100.0. "
            "(4) `created_at` is UTC but Finance reports on America/Los_Angeles "
            "days, so convert the timezone before truncating to a date."
        ),
        "ground_truth": textwrap.dedent(
            """\
            SELECT DATE_TRUNC('day', created_at AT TIME ZONE 'America/Los_Angeles') AS day,
                   SUM(amount) / 100.0 AS revenue_usd
            FROM fct_orders_v2
            WHERE is_test = FALSE
              AND created_at >= NOW() - INTERVAL '7 days'
            GROUP BY 1
            ORDER BY 1;"""
        ),
    },
    {
        "question": "How many orders did each region place last month?",
        # Round 2's feedback is generated at runtime from the grader — see
        # round_two_feedback(). Hardcoding "you got it wrong again" would make the
        # demo assert something false the moment the playbook actually works.
        "ground_truth": textwrap.dedent(
            """\
            SELECT c.region,
                   COUNT(*) AS order_count
            FROM fct_orders_v2 o
            JOIN dim_customers c USING (customer_id)
            WHERE o.is_test = FALSE
              AND DATE_TRUNC('month', o.created_at AT TIME ZONE 'America/Los_Angeles')
                  = DATE_TRUNC('month', (NOW() AT TIME ZONE 'America/Los_Angeles') - INTERVAL '1 month')
            GROUP BY 1
            ORDER BY 2 DESC;"""
        ),
    },
]

HELD_OUT = (
    "Break down revenue in dollars by channel for each day of July 2026."
)


def round_two_feedback(sql: str) -> tuple[str, bool]:
    """
    Grade round 2 and write the feedback the senior analyst would actually give.

    Both branches are real ACE: reinforcing a strategy that worked bumps a
    bullet's `helpful` counter, correcting one adds or revises bullets.
    """
    # Round 2 asks for a COUNT, so the cents-to-dollars rule is out of scope.
    missed = [rule for rule, ok in grade(sql, reports_money=False) if not ok]
    if not missed:
        return (
            "Correct — and note that I never told you any of this for a *count* "
            "query. You carried the house rules over from a revenue question to a "
            "different question type on your own. That is exactly the behaviour I "
            "want: these rules are properties of the warehouse, not of any one "
            "question. You were also right to leave the cents conversion out — a "
            "row count is not a dollar figure. Apply each rule wherever it binds.",
            True,
        )
    detail = "; ".join(f"{r.name} ({r.statement})" for r in missed)
    return (
        "You slipped on rules you have already been told. Still missing: "
        f"{detail}. The house rules are not per-question — they hold for every "
        "query against this warehouse, counts included.",
        False,
    )


def report_card(label: str, sql: str, reports_money: bool = True) -> int:
    results = grade(sql, reports_money)
    got = sum(1 for _, ok in results if ok)
    total = len(applicable(reports_money))
    scope = "" if reports_money else " (cents rule n/a — this is a count)"
    print(f"{BOLD}   {label}: {got}/{total} applicable house rules followed{scope}{RESET}")
    for rule, ok in results:
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"     {mark} {rule.name}")
    print()
    return got


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


def main() -> int:
    if not os.getenv("ANTHROPIC_API_KEY"):
        print(f"{RED}ANTHROPIC_API_KEY not found — check your .env file.{RESET}")
        return 1

    print(f"\n{BOLD}Agentic Context Engineering — live demo{RESET}")
    print(f"{DIM}model: {MODEL}{RESET}")
    print(
        textwrap.fill(
            "Both agents below are the same model with the same system prompt. "
            "The only thing that will differ is the context one of them has "
            "written for itself.",
            width=74,
        )
    )
    print(f"\n{DIM}The four house rules — the agent is never shown these:{RESET}")
    for rule in RULES:
        print(f"{DIM}   • {rule.statement}{RESET}")
    pause()

    # -- ACT I -------------------------------------------------------------
    act("I", "The cold agent — capable, and confidently wrong")

    learner = ACELiteLLM(model=MODEL, temperature=TEMPERATURE, max_tokens=8192)

    step(f"Asking (round 1): {TRAIN[0]['question']}")
    t0 = time.time()
    answer = learner.ask(TRAIN[0]["question"], context=SYSTEM_CONTEXT)
    print(f"{DIM}   ({time.time() - t0:.1f}s){RESET}\n")
    quote(answer)
    report_card("cold agent", answer)
    print(
        textwrap.fill(
            "It is not a bad query. It is a query written by someone who has "
            "never worked here. No amount of extra reasoning fixes that — the "
            "information simply is not in the weights.",
            width=74,
        )
    )
    pause()

    # -- ACT II ------------------------------------------------------------
    act("II", "Reflect and curate — turning feedback into a playbook")

    step("Sending the senior analyst's feedback to the Reflector...")
    quote(textwrap.fill(TRAIN[0]["feedback"], width=64))
    learner.learn_from_feedback(
        feedback=TRAIN[0]["feedback"], ground_truth=TRAIN[0]["ground_truth"]
    )
    print(f"{GREEN}   Reflector → SkillManager → playbook updated.{RESET}\n")
    step(f"Playbook now holds {len(learner.skillbook.skills())} strategies:")
    quote(learner.get_strategies(), color=CYAN)
    pause()

    step(f"Round 2 — a different question: {TRAIN[1]['question']}")
    answer2 = learner.ask(TRAIN[1]["question"], context=SYSTEM_CONTEXT)
    quote(answer2)
    report_card("agent with 1 round of feedback", answer2, reports_money=False)

    feedback2, was_right = round_two_feedback(answer2)
    if was_right:
        step("It transferred the rules to a question type it was never taught.")
        step("So the feedback is reinforcement, not correction:")
    else:
        step("Still slipping — so the feedback corrects the gaps:")
    quote(textwrap.fill(feedback2, width=64))
    learner.learn_from_feedback(
        feedback=feedback2,
        ground_truth=None if was_right else TRAIN[1]["ground_truth"],
    )
    print(
        textwrap.fill(
            "The Curator does not overwrite the playbook — it applies a delta. "
            "Existing bullets are kept, reinforced, or retired individually. "
            "That is the paper's answer to context collapse.",
            width=74,
        )
    )
    print()
    step(f"Playbook now holds {len(learner.skillbook.skills())} strategies:")
    quote(learner.get_strategies(), color=CYAN)
    learner.save_skillbook(SKILLBOOK_PATH)
    print(f"{DIM}   saved → {SKILLBOOK_PATH}{RESET}")
    pause()

    # -- ACT III -----------------------------------------------------------
    act("III", "The held-out question — same model, different context")

    print(f"{BOLD}Question neither agent has seen:{RESET}")
    quote(HELD_OUT)

    step("Agent A — fresh instance, empty playbook (the control)")
    control = ACELiteLLM(model=MODEL, temperature=TEMPERATURE, max_tokens=8192, is_learning=False)
    control_answer = control.ask(HELD_OUT, context=SYSTEM_CONTEXT)
    quote(control_answer)
    control_score = report_card("Agent A (no playbook)", control_answer)

    step("Agent B — fresh instance, loaded with the saved playbook")
    trained = ACELiteLLM(
        model=MODEL,
        temperature=TEMPERATURE,
        max_tokens=8192,
        skillbook_path=SKILLBOOK_PATH,
        is_learning=False,
    )
    trained_answer = trained.ask(HELD_OUT, context=SYSTEM_CONTEXT)
    quote(trained_answer)
    trained_score = report_card("Agent B (with playbook)", trained_answer)

    # -- CLOSE -------------------------------------------------------------
    act("IV", "What just happened")

    print(f"{BOLD}   Agent A: {control_score}/{len(RULES)}    "
          f"Agent B: {trained_score}/{len(RULES)}{RESET}\n")
    print(
        textwrap.fill(
            "Same model. Same weights. Same question. The delta is entirely "
            "context that the agent generated, curated and persisted for itself "
            "from two rounds of feedback — no gradient updates, no retraining, "
            "and the whole playbook is a JSON file you can open and read.",
            width=74,
        )
    )
    print(f"\n{DIM}   Open {SKILLBOOK_PATH} to see the learned strategies.{RESET}")
    print(f"{DIM}   Read ACE_EXPLAINED.md for how the three roles fit together.{RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
