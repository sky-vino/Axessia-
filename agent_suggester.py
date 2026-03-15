# ======================================================
# AXESSIA – Agent Suggester (Azure OpenAI)
# ======================================================

import os
from openai import AzureOpenAI

_az_client = None


def _get_client() -> AzureOpenAI:
    global _az_client
    if _az_client is None:
        _az_client = AzureOpenAI(
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key        = os.getenv("AZURE_OPENAI_KEY"),
            api_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
    return _az_client


MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def suggest_fix(rule: dict, instance: dict) -> str:
    """
    Returns a concrete remediation suggestion.
    Does NOT alter compliance status, score, or priority.
    """
    prompt = f"""
You are an accessibility engineer.

Provide a concrete remediation suggestion for the issue below.
Be concise and actionable. Do NOT change compliance decisions.

Rule:
- Name: {rule.get('name', '')}
- WCAG: {rule.get('wcag', '')} (Level {rule.get('level', '')})
- Severity: {rule.get('severity', '')}

Evidence:
- Description: {instance.get('reason', '')}
- HTML snippet:
{instance.get('snippet', instance.get('tag', ''))}

Output requirements:
- Step-by-step fix guidance
- Include example code if helpful
- Avoid tool references
"""
    try:
        response = _get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            timeout=10,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Fix suggestion unavailable at the moment."
