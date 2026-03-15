# ======================================================
# AXESSIA – Azure OpenAI Client
# All credentials come from Azure App Service → Configuration
# ======================================================

import os
from openai import AzureOpenAI
from functools import lru_cache

# ── Client ────────────────────────────────────────────
client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key        = os.getenv("AZURE_OPENAI_KEY"),
    api_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
)

MODEL   = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
TIMEOUT = 20


# ── Generic helper (used by ai_agent.py) ──────────────
def ask_openai(prompt: str, system: str = "You are an accessibility expert.") -> str:
    """Generic single-turn call. Returns text or a safe fallback."""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": prompt},
            ],
            timeout=TIMEOUT,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "AI explanation unavailable at the moment."


# ── Cached specialist functions ────────────────────────

@lru_cache(maxsize=256)
def explain_issue(rule, severity, instances, url):
    """AI explanation for automated failures."""
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
    return ask_openai(prompt, "You are a WCAG 2.2 accessibility specialist.")


@lru_cache(maxsize=256)
def explain_manual_check(rule, url):
    """Why manual review is required + how to test."""
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
    return ask_openai(prompt, "You are a senior accessibility auditor.")


@lru_cache(maxsize=128)
def generate_test_cases(rule, severity):
    """Manual test cases table for AI Agent tab."""
    prompt = f"""
Create manual accessibility test cases for the following rule.

Rule: {rule}
Severity: {severity}

Return a table with columns:
- Step
- Action
- Expected Result
"""
    return ask_openai(prompt, "You generate accessibility test cases.")
