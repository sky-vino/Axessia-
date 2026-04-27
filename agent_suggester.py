# agent_suggester.py
# Layer 8 – AI remediation suggestions (non-destructive)

import os
from openai import OpenAI

_client = None

def _client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def suggest_fix(rule: dict, instance: dict) -> str:
    """
    Returns a remediation suggestion.
    Must NOT alter status/score/priority.
    """
    prompt = f"""
You are an accessibility engineer.

Provide a concrete remediation suggestion for the issue below.
Be concise and actionable. Do NOT change compliance decisions.

Rule:
- Name: {rule['name']}
- WCAG: {rule['wcag']} (Level {rule['level']})
- Severity: {rule['severity']}

Evidence:
- Description: {instance.get('reason', '')}
- HTML:
{instance.get('tag', '')}

Output requirements:
- Step-by-step fix guidance
- Include example code if helpful
- Avoid tool references
"""
    r = _client().chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
        timeout=8,
    )
    return r.choices[0].message.content.strip()
