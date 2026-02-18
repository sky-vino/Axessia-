import os
import hashlib
from openai import OpenAI
from functools import lru_cache

# Read key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"  # fast, cheap, good for explanations
TIMEOUT = 15


def _cache_key(*parts):
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


@lru_cache(maxsize=256)
def explain_issue(rule, severity, instances, url):
    """
    AI explanation for automated failures
    """
    prompt = f"""
You are an accessibility expert.

Explain the following WCAG issue clearly and concisely.

Website: {url}
Rule: {rule}
Severity: {severity}
Number of instances: {instances}

Explain:
1. Why this is an accessibility problem
2. Who is impacted
3. High-level remediation guidance (no code)

Avoid generic statements. Be specific.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a WCAG 2.2 accessibility specialist."},
                {"role": "user", "content": prompt},
            ],
            timeout=TIMEOUT,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return (
            "This issue impacts accessibility and requires remediation. "
            "AI explanation unavailable at the moment."
        )


@lru_cache(maxsize=256)
def explain_manual_check(rule, url):
    """
    Why manual review is required + how to test
    """
    prompt = f"""
You are an accessibility auditor.

This rule requires manual verification.

Website: {url}
Rule: {rule}

Explain:
1. Why automation cannot reliably determine pass/fail
2. How a human should test this (keyboard, screen reader, zoom, etc.)
3. What constitutes pass vs fail

Use bullet points.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a senior accessibility auditor."},
                {"role": "user", "content": prompt},
            ],
            timeout=TIMEOUT,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return (
            "This check requires human judgment. "
            "Manual testing is recommended using assistive technologies."
        )


@lru_cache(maxsize=128)
def generate_test_cases(rule, severity):
    """
    Manual test cases table for AI Agent tab
    """
    prompt = f"""
Create manual accessibility test cases for the following rule.

Rule: {rule}
Severity: {severity}

Return a table with columns:
- Step
- Action
- Expected Result
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You generate accessibility test cases."},
                {"role": "user", "content": prompt},
            ],
            timeout=TIMEOUT,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        return "Manual test cases unavailable."
