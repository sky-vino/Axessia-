# ======================================================
# AXESSIA – AI QA Test Case Generator (Azure OpenAI)
# ======================================================

import os
import json
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key        = os.getenv("AZURE_OPENAI_KEY"),
    api_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
)

MODEL = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")


def generate_qa_test(rule_name: str, wcag_sc: str) -> dict:
    prompt = f"""
You are an accessibility QA lead.

Create a DEEP, step-by-step manual test case for the following rule.

Rule: {rule_name}
WCAG Success Criterion: {wcag_sc}

The test must be executable by a junior QA with NO accessibility background.

Return ONLY valid JSON in this exact format (no markdown, no extra text):

{{
  "Scenario": "...",
  "Steps": [
    "Step 1 ...",
    "Step 2 ...",
    "Step 3 ..."
  ],
  "Expected Result": "..."
}}
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are an expert accessibility QA engineer. Return ONLY valid JSON."},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())

    except Exception:
        return {
            "Scenario": rule_name,
            "Steps": [
                "Navigate using keyboard only (Tab / Shift+Tab)",
                "Use a screen reader to identify the element",
                "Verify the announced name and role are correct",
            ],
            "Expected Result": "Element is perceivable, operable, and understandable.",
        }
