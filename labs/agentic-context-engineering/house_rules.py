"""
The hidden domain knowledge for the demo.

These are the four "house rules" of a fictional company's data warehouse.
They are deliberately *unknowable* to a pretrained model: internal table
names, an internal test-row flag, a storage unit convention, and a reporting
timezone. No amount of raw model capability gets these right on the first
try — the only way to know them is to be told.

That is exactly the gap ACE is designed to close. The rules live here so the
demo can (a) build ground-truth answers and (b) objectively grade whether a
generated query followed them.
"""

import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Rule:
    name: str
    statement: str
    # Returns True if the SQL appears to respect the rule.
    check: Callable[[str], bool]
    # Some rules only bind on queries that report a dollar figure. Grading a
    # COUNT query against the cents rule would mark a correct answer wrong and
    # then "teach" the agent to divide a row count by 100.
    money_only: bool = False


def _has(sql: str, pattern: str) -> bool:
    return re.search(pattern, sql, re.IGNORECASE | re.DOTALL) is not None


RULES = [
    Rule(
        name="fct_orders_v2",
        statement=(
            "Always query `fct_orders_v2`. The `orders` table is deprecated and "
            "silently missing all marketplace channels."
        ),
        check=lambda sql: _has(sql, r"fct_orders_v2"),
    ),
    Rule(
        name="exclude test rows",
        statement=(
            "Every revenue or count query must filter out `is_test = TRUE`. "
            "Load-testing writes millions of fake orders into production."
        ),
        check=lambda sql: _has(sql, r"is_test\s*(=\s*(false|0)|IS\s+NOT\s+TRUE)|NOT\s+is_test"),
    ),
    Rule(
        name="cents -> dollars",
        statement=(
            "`amount` is stored as an INTEGER number of cents. Divide by 100.0 "
            "before reporting any dollar figure."
        ),
        check=lambda sql: _has(sql, r"/\s*100(\.0)?"),
        money_only=True,
    ),
    Rule(
        name="UTC -> America/Los_Angeles",
        statement=(
            "`created_at` is UTC. Finance reports on America/Los_Angeles days, so "
            "convert the timestamp before truncating to a date."
        ),
        check=lambda sql: _has(sql, r"America/Los_Angeles"),
    ),
]


# The schema the agent is shown. Note what is NOT here: no `fct_orders_v2`, no
# `is_test` column, no hint that `amount` is in cents or that `created_at` is UTC.
# The published docs are out of date — which is the normal state of a data
# warehouse, and precisely the knowledge a playbook has to carry.
SCHEMA = """\
-- Data dictionary (last reviewed 14 months ago)
orders(order_id BIGINT, customer_id BIGINT, channel TEXT,
       amount BIGINT, created_at TIMESTAMP)
dim_customers(customer_id BIGINT, region TEXT, signup_date DATE)
"""


def applicable(reports_money: bool) -> list[Rule]:
    """The rules that actually bind on a query of this kind."""
    return [r for r in RULES if reports_money or not r.money_only]


def grade(sql: str, reports_money: bool = True) -> list[tuple[Rule, bool]]:
    """
    Score a generated query against the house rules that apply to it.

    `reports_money=False` for queries that return counts rather than dollar
    figures — the cents-to-dollars rule is not in scope for those.
    """
    return [(rule, rule.check(sql)) for rule in applicable(reports_money)]


def score(sql: str, reports_money: bool = True) -> int:
    return sum(1 for _, ok in grade(sql, reports_money) if ok)
