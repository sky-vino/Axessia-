# ai_explainer.py
# Real Azure OpenAI explanations with failing HTML context
# Cached in SQLite to avoid repeated API calls for same rule+snippet

import os
import hashlib
import json
import sqlite3
import logging
from openai import AzureOpenAI

log = logging.getLogger(__name__)

# ── Azure OpenAI client ────────────────────────────────
def _get_client():
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    )

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
TIMEOUT    = 20

# ── SQLite cache ───────────────────────────────────────
_DB_PATH = "ai_cache.db"

def _db():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS explain_cache (
            cache_key TEXT PRIMARY KEY,
            payload   TEXT,
            created   DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def _cache_key(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

def _get_cached(key: str):
    try:
        conn = _db()
        row = conn.execute(
            "SELECT payload FROM explain_cache WHERE cache_key=?", (key,)
        ).fetchone()
        conn.close()
        return json.loads(row[0]) if row else None
    except Exception:
        return None

def _set_cached(key: str, payload: dict):
    try:
        conn = _db()
        conn.execute(
            "INSERT OR REPLACE INTO explain_cache (cache_key, payload) VALUES (?,?)",
            (key, json.dumps(payload))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Core explanation function ──────────────────────────
def explain_rule(rule: dict, page_url: str) -> dict:
    """
    Generates AI-powered explanation for a failing rule.
    Uses the actual failing HTML snippet for context.
    Returns structured dict with dev + QA framing.
    """
    rule_id       = rule.get("id", "")
    rule_name     = rule.get("name", rule_id)
    wcag          = rule.get("wcag", "")
    severity      = rule.get("severity", "moderate")
    test_type     = rule.get("test_type", "automated")
    instance_count= rule.get("instance_count", 0)
    instances     = rule.get("instances", [])

    # Build snippet from first 3 failing instances
    snippet = ""
    if instances:
        snippets = [
            inst.get("snippet", "")
            for inst in instances[:3]
            if inst.get("snippet")
        ]
        snippet = "\n".join(snippets)

    cache_key = _cache_key(rule_id, wcag, severity, snippet[:200])
    cached    = _get_cached(cache_key)
    if cached:
        return cached

    # Build the prompt with real HTML context
    snippet_section = f"\n\nFailing HTML (first instances):\n```html\n{snippet}\n```" if snippet else ""

    prompt = f"""You are a senior WCAG 2.2 accessibility specialist reviewing a real accessibility failure.

Rule Failed: {rule_name}
WCAG Criterion: {wcag}
Severity: {severity}
Test Type: {test_type}
Number of failing instances: {instance_count}
Page URL: {page_url}{snippet_section}

Provide a structured accessibility analysis with these exact sections:

USER_IMPACT: One sentence describing who is affected and how.
WHY_IT_MATTERS: One sentence on the functional/legal consequence.
DEV_ACTION: 2-3 specific, actionable steps for the developer to fix this. Reference the failing HTML if provided.
QA_STEPS: 2-3 specific test steps for a QA tester to verify the fix.
EAA_CONTEXT: One sentence on EAA / EN 301 549 relevance.
CONTRAST_RATIO: Only if this is a colour contrast issue, include "Actual: X:1 | Required: 4.5:1". Otherwise write "N/A".

Be specific to the actual HTML shown. Do not give generic advice."""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {"role": "system", "content": "You are a WCAG 2.2 accessibility specialist. Be concise and specific."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.2,
        )
        text = response.choices[0].message.content.strip()
        result = _parse_ai_response(text, rule_name, wcag, test_type)
    except Exception as e:
        log.warning(f"AI explanation failed for {rule_id}: {e}")
        result = _fallback_explanation(rule_name, wcag, severity, test_type, instance_count)

    _set_cached(cache_key, result)
    return result


def _parse_ai_response(text: str, rule_name: str, wcag: str, test_type: str) -> dict:
    """Parse structured AI response into dict."""
    sections = {
        "user_impact": "",
        "why_it_matters": "",
        "dev_action": "",
        "qa_steps": "",
        "eaa_context": "",
        "contrast_ratio": "N/A",
    }

    current = None
    buffer  = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("USER_IMPACT:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "user_impact", [stripped[len("USER_IMPACT:"):].strip()]
        elif stripped.startswith("WHY_IT_MATTERS:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "why_it_matters", [stripped[len("WHY_IT_MATTERS:"):].strip()]
        elif stripped.startswith("DEV_ACTION:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "dev_action", [stripped[len("DEV_ACTION:"):].strip()]
        elif stripped.startswith("QA_STEPS:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "qa_steps", [stripped[len("QA_STEPS:"):].strip()]
        elif stripped.startswith("EAA_CONTEXT:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "eaa_context", [stripped[len("EAA_CONTEXT:"):].strip()]
        elif stripped.startswith("CONTRAST_RATIO:"):
            if current: sections[current] = "\n".join(buffer).strip()
            current, buffer = "contrast_ratio", [stripped[len("CONTRAST_RATIO:"):].strip()]
        elif current:
            buffer.append(stripped)

    if current:
        sections[current] = "\n".join(buffer).strip()

    # QA validation steps as list
    qa_raw = sections.get("qa_steps", "")
    qa_steps = [
        s.lstrip("0123456789.-) ").strip()
        for s in qa_raw.splitlines()
        if s.strip() and not s.strip().startswith("#")
    ]

    return {
        "user_impact":    sections["user_impact"]    or f"Users relying on assistive technology are affected by this {rule_name} failure.",
        "why_it_matters": sections["why_it_matters"]  or f"WCAG {wcag} is required under EAA/EN 301 549.",
        "dev_action":     sections["dev_action"]      or "Review and fix the failing elements to meet WCAG requirements.",
        "qa_steps":       qa_steps or ["Test with keyboard navigation.", "Test with screen reader.", "Verify with automated tool."],
        "eaa_context":    sections["eaa_context"]     or f"WCAG {wcag} is a mandatory requirement under the European Accessibility Act.",
        "contrast_ratio": sections["contrast_ratio"]  or "N/A",
        "what_to_test_manually": sections["qa_steps"] or "",
        "who_is_impacted": sections["user_impact"] or "",
        "legal_risk": sections["eaa_context"] or "",
        "why_not_automated": (
            "This rule cannot be fully automated because compliance depends on user interaction or visual perception."
            if test_type != "automated"
            else "This rule is automatically detectable."
        ),
    }


def _fallback_explanation(rule_name, wcag, severity, test_type, instance_count) -> dict:
    """Static fallback when AI is unavailable."""
    impact_map = {
        "critical": "This critical failure blocks access for users relying on assistive technologies.",
        "serious":  "This serious failure significantly impairs accessibility for affected users.",
        "moderate": "This moderate failure creates barriers that reduce usability for some users.",
        "minor":    "This minor issue may cause confusion or inconvenience for some users.",
    }
    return {
        "user_impact":    impact_map.get(severity, impact_map["moderate"]),
        "why_it_matters": f"WCAG {wcag} is mandatory under the European Accessibility Act (EAA) and EN 301 549.",
        "dev_action":     f"Review all {instance_count} failing instance(s) of '{rule_name}' and apply the WCAG {wcag} success criterion.",
        "qa_steps":       ["Test with keyboard navigation.", "Test with NVDA + Chrome or VoiceOver + Safari.", "Re-run automated scan to confirm resolution."],
        "eaa_context":    f"WCAG {wcag} is a mandatory requirement under the European Accessibility Act.",
        "contrast_ratio": "N/A",
        "what_to_test_manually": f"Manually verify '{rule_name}' by testing real user flows with keyboard and screen reader.",
        "who_is_impacted": "Users relying on keyboards, screen readers, or other assistive technologies.",
        "legal_risk": f"Failure to meet WCAG {wcag} exposes the organisation to EAA non-compliance risk.",
        "why_not_automated": (
            f"The rule '{rule_name}' requires human judgment to fully evaluate."
            if test_type != "automated"
            else "This rule is automatically detectable by axe-core."
        ),
    }
