#!/usr/bin/env python3
# cicd_runner.py
# Axessia CI/CD CLI — run accessibility scan from GitHub Actions or Azure DevOps
#
# Usage:
#   python cicd_runner.py --url https://example.com [options]
#
# Exit codes:
#   0 = all checks pass (or only minor/moderate issues)
#   1 = critical or serious failures found (blocks pipeline)
#   2 = scan error

import argparse
import json
import sys
import os
import requests
from datetime import datetime


def run_scan(url: str, api_url: str, api_key: str, timeout: int = 120) -> dict | None:
    try:
        resp = requests.post(
            api_url,
            headers={"Content-Type": "application/json", "x-api-key": api_key},
            json={"url": url},
            timeout=timeout,
        )
        if resp.status_code != 200:
            print(f"[AXESSIA] Scan failed: HTTP {resp.status_code}", file=sys.stderr)
            return None
        return resp.json()
    except Exception as e:
        print(f"[AXESSIA] Scan error: {e}", file=sys.stderr)
        return None


def evaluate_result(result: dict, fail_on: str) -> tuple[int, dict]:
    """
    Evaluate scan result against threshold.
    Returns (exit_code, summary)
    """
    rules    = result.get("rules", [])
    failures = [r for r in rules if r.get("status") == "fail"]

    sev_counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
    for r in failures:
        sev = r.get("severity", "moderate")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    critical = sev_counts["critical"]
    serious  = sev_counts["serious"]

    # Exit code logic
    if fail_on == "critical" and critical > 0:
        exit_code = 1
    elif fail_on == "serious" and (critical + serious) > 0:
        exit_code = 1
    elif fail_on == "any" and failures:
        exit_code = 1
    else:
        exit_code = 0

    # Score
    from scoring import calculate_score
    import pandas as pd
    score_data = calculate_score(rules)
    score      = score_data.get("score", 0)

    summary = {
        "url":       result.get("url", ""),
        "score":     score,
        "failures":  len(failures),
        "critical":  critical,
        "serious":   serious,
        "moderate":  sev_counts["moderate"],
        "minor":     sev_counts["minor"],
        "pass":      exit_code == 0,
        "threshold": fail_on,
        "scanned_at": datetime.now().isoformat(),
    }
    return exit_code, summary


def output_sarif(result: dict, url: str) -> str:
    """Output SARIF format for GitHub Code Scanning."""
    rules_map = {}
    runs_results = []

    for rule in result.get("rules", []):
        if rule.get("status") != "fail":
            continue

        rule_id = rule.get("id", "unknown")
        if rule_id not in rules_map:
            rules_map[rule_id] = {
                "id":               rule_id,
                "name":             rule.get("name", rule_id),
                "shortDescription": {"text": rule.get("name", rule_id)},
                "fullDescription":  {"text": rule.get("description", rule.get("name", ""))},
                "helpUri":          rule.get("help_url", "https://www.w3.org/WAI/WCAG22/"),
                "properties":       {"tags": ["accessibility", f"wcag:{rule.get('wcag','')}", rule.get("severity","")]},
                "defaultConfiguration": {
                    "level": "error" if rule.get("severity") in ("critical","serious") else "warning"
                },
            }

        for inst in (rule.get("instances") or [{}])[:3]:
            runs_results.append({
                "ruleId":  rule_id,
                "message": {"text": f"{rule.get('name')} — WCAG {rule.get('wcag','—')} — {rule.get('severity','').upper()}"},
                "level":   "error" if rule.get("severity") in ("critical","serious") else "warning",
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": url},
                    },
                    "logicalLocations": [{
                        "name": inst.get("selector", url),
                        "kind": "htmlElement",
                    }],
                }],
                "partialFingerprints": {"snippet": (inst.get("snippet","") or "")[:100]},
            })

    sarif = {
        "version": "2.1.0",
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name":            "Axessia",
                    "version":         "1.0.0",
                    "informationUri":  "https://github.com/sky-vino/Axessia-",
                    "rules":           list(rules_map.values()),
                }
            },
            "results": runs_results,
            "originalUriBaseIds": {"SRCROOT": {"uri": url}},
        }]
    }
    return json.dumps(sarif, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Axessia CI/CD — Accessibility gate for pipelines"
    )
    parser.add_argument("--url",      required=True, help="URL to scan")
    parser.add_argument("--api-url",  default=os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan"))
    parser.add_argument("--api-key",  default=os.getenv("AXESSIA_API_KEY", "super-secret-demo-key"))
    parser.add_argument("--fail-on",  default="critical",
                        choices=["critical", "serious", "any", "none"],
                        help="Severity threshold to fail the pipeline (default: critical)")
    parser.add_argument("--output",   default="text", choices=["text", "json", "sarif"],
                        help="Output format")
    parser.add_argument("--out-file", default=None, help="Write output to file")
    parser.add_argument("--timeout",  type=int, default=120)
    args = parser.parse_args()

    print(f"[AXESSIA] Scanning: {args.url}", file=sys.stderr)
    print(f"[AXESSIA] Threshold: fail on {args.fail_on}", file=sys.stderr)

    result = run_scan(args.url, args.api_url, args.api_key, args.timeout)
    if result is None:
        sys.exit(2)

    if result.get("error"):
        print(f"[AXESSIA] Error: {result['error']}", file=sys.stderr)
        sys.exit(2)

    exit_code, summary = evaluate_result(result, args.fail_on)

    # Format output
    if args.output == "json":
        output = json.dumps({"summary": summary, "details": result}, indent=2)
    elif args.output == "sarif":
        output = output_sarif(result, args.url)
    else:
        lines = [
            f"\n{'='*55}",
            f"  AXESSIA Accessibility Scan — {summary['url'][:45]}",
            f"{'='*55}",
            f"  Score:     {summary['score']}%",
            f"  Critical:  {summary['critical']}",
            f"  Serious:   {summary['serious']}",
            f"  Moderate:  {summary['moderate']}",
            f"  Minor:     {summary['minor']}",
            f"  Threshold: fail on {summary['threshold']}",
            f"  Result:    {'✅ PASS' if summary['pass'] else '❌ FAIL — pipeline blocked'}",
            f"{'='*55}\n",
        ]
        output = "\n".join(lines)

    if args.out_file:
        with open(args.out_file, "w") as f:
            f.write(output)
        print(f"[AXESSIA] Output written to {args.out_file}", file=sys.stderr)
    else:
        print(output)

    print(f"[AXESSIA] Exiting with code {exit_code}", file=sys.stderr)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
