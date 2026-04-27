# ai_agent.py
from openai_client import ask_openai

def explain_issue(rule, wcag, severity, instances, url):
    prompt = f"""
Website URL: {url}

Accessibility rule failed: {rule}
WCAG references: {wcag}
Severity: {severity}
Number of affected instances: {instances}

Explain:
1. Why this issue occurs on real websites
2. Which users are impacted
3. Practical remediation guidance

Do NOT guess HTML.
Do NOT claim compliance.
"""
    return ask_openai(prompt)


def explain_manual(rule, wcag, severity, url):
    prompt = f"""
Website URL: {url}

Accessibility check requiring manual validation: {rule}
WCAG references: {wcag}
Severity: {severity}

Explain:
1. Why automation cannot reliably verify this
2. What human testers should validate
3. Common real-world failures

Be practical and concise.
"""
    return ask_openai(prompt)


def generate_test_cases(rule, wcag, url):
    prompt = f"""
Website URL: {url}

Accessibility area: {rule}
WCAG references: {wcag}

Generate manual accessibility test cases in a table format with:
- Step
- Action
- Expected Result

Focus on keyboard and screen reader validation.
"""
    text = ask_openai(prompt)

    # Convert text into rows (simple split for Streamlit table)
    rows = []
    for i, line in enumerate(text.split("\n")):
        if line.strip():
            rows.append({
                "Step": i + 1,
                "Action / Expectation": line.strip()
            })
    return rows


def priority_score(severity, instances):
    base = {
        "critical": 100,
        "serious": 70,
        "moderate": 40,
        "minor": 20
    }.get(severity, 30)

    return base + (instances * 5 if isinstance(instances, int) else 0)
