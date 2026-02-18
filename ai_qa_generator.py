from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_qa_test(rule_name: str, wcag_sc: str) -> dict:
    prompt = f"""
You are an accessibility QA lead.

Create a DEEP, step-by-step manual test case for the following rule.

Rule: {rule_name}
WCAG Success Criterion: {wcag_sc}

The test must be executable by a junior QA with NO accessibility background.

Return the answer in this exact JSON format:

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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert accessibility QA engineer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    content = response.choices[0].message.content

    # Safe parse fallback
    try:
        import json
        return json.loads(content)
    except Exception:
        return {
            "Scenario": rule_name,
            "Steps": [
                "Navigate using keyboard only",
                "Use screen reader to identify element",
                "Verify announced name and role"
            ],
            "Expected Result": "Element is perceivable, operable, and understandable"
        }
