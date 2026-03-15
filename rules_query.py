# rules_query.py
from rules_registry import RULES


def get_rules_by_type(test_type: str):
    return [r for r in RULES if r["test_type"] == test_type]


def get_all_rules():
    return RULES
