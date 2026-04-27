# pdf_report.py
# Axessia — Full Accessibility Evidence Report (PDF)
# Includes: screenshots, contrast ratios, AI explanations, EAA status

import base64
import io
from datetime import datetime
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
import pandas as pd


# ── Colour palette ─────────────────────────────────────
SKY_PURPLE  = colors.HexColor("#8B2FC9")
SKY_MAGENTA = colors.HexColor("#C8196E")
SKY_BLUE    = colors.HexColor("#1C6FD4")
SKY_RED     = colors.HexColor("#E8192C")

SEV_COLORS = {
    "critical": colors.HexColor("#E24B4A"),
    "serious":  colors.HexColor("#EF9F27"),
    "moderate": colors.HexColor("#378ADD"),
    "minor":    colors.HexColor("#639922"),
}

PASS_GREEN  = colors.HexColor("#1D9E75")
FAIL_RED    = colors.HexColor("#E24B4A")
LIGHT_GRAY  = colors.HexColor("#F5F5F8")
BORDER_GRAY = colors.HexColor("#DDDDEE")
TEXT_DARK   = colors.HexColor("#1A1A2E")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "title":    ParagraphStyle("title",    parent=base["Title"],   fontSize=20, textColor=SKY_PURPLE, spaceAfter=6),
        "h1":       ParagraphStyle("h1",       parent=base["Heading1"], fontSize=14, textColor=SKY_PURPLE, spaceAfter=4),
        "h2":       ParagraphStyle("h2",       parent=base["Heading2"], fontSize=11, textColor=SKY_MAGENTA, spaceAfter=3),
        "body":     ParagraphStyle("body",     parent=base["Normal"],  fontSize=9,  spaceAfter=3, textColor=TEXT_DARK),
        "code":     ParagraphStyle("code",     parent=base["Code"],    fontSize=7.5, backColor=LIGHT_GRAY, leftIndent=8, rightIndent=8),
        "caption":  ParagraphStyle("caption",  parent=base["Normal"],  fontSize=8,  textColor=colors.gray),
        "label":    ParagraphStyle("label",    parent=base["Normal"],  fontSize=8.5, textColor=colors.gray, spaceAfter=1),
        "severity": ParagraphStyle("severity", parent=base["Normal"],  fontSize=9,  fontName="Helvetica-Bold"),
        "mono":     ParagraphStyle("mono",     parent=base["Code"],    fontSize=7,  fontName="Courier", backColor=LIGHT_GRAY),
    }
    return styles


def _severity_badge(sev: str) -> str:
    c = {"critical": "#E24B4A", "serious": "#EF9F27", "moderate": "#378ADD", "minor": "#639922"}.get(sev, "#888")
    return f'<font color="{c}"><b>{sev.upper()}</b></font>'


def _status_badge(status: str) -> str:
    if status == "fail":   return '<font color="#E24B4A"><b>FAIL</b></font>'
    if status == "pass":   return '<font color="#1D9E75"><b>PASS</b></font>'
    return f'<font color="#EF9F27"><b>{status.upper()}</b></font>'


def _screenshot_image(b64: str | None, max_width: float = 160*mm, max_height: float = 80*mm):
    """Convert base64 PNG to ReportLab Image."""
    if not b64:
        return None
    try:
        img_bytes = base64.b64decode(b64)
        buf = io.BytesIO(img_bytes)
        img = Image(buf)
        # Scale proportionally
        w, h = img.drawWidth, img.drawHeight
        scale = min(max_width / w, max_height / h, 1.0)
        img.drawWidth  = w * scale
        img.drawHeight = h * scale
        return img
    except Exception:
        return None


def generate_pdf_report(url: str, scan_data: dict) -> bytes:
    """
    Generate a full Axessia accessibility evidence report as PDF bytes.
    Includes screenshots, contrast ratios, AI explanations.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=15*mm,  bottomMargin=15*mm,
    )

    S     = _styles()
    story = []

    rules = scan_data.get("rules", [])
    df    = pd.DataFrame(rules) if rules else pd.DataFrame()

    page_title   = scan_data.get("page_title", "—")
    viewports    = scan_data.get("viewports_tested", ["desktop"])
    axe_version  = scan_data.get("axe_version", "4.9.0")
    page_shot    = scan_data.get("page_screenshot")
    mobile_shot  = scan_data.get("mobile_screenshot")

    failures     = [r for r in rules if r.get("status") == "fail"]
    manual_items = [r for r in rules if r.get("test_type") in ("manual", "assisted")]
    passed       = [r for r in rules if r.get("status") == "pass" and r.get("test_type") == "automated"]

    # ── EAA + Score ─────────────────────────────────
    from eaa_mapping import evaluate_eaa
    from scoring import calculate_score
    eaa   = evaluate_eaa(rules) if rules else {}
    score = calculate_score(rules) if rules else {}

    # ════════════════════════════════════════════════
    # COVER PAGE
    # ════════════════════════════════════════════════
    story.append(Paragraph("Axessia — Accessibility Assessment Report", S["title"]))
    story.append(HRFlowable(width="100%", thickness=2, color=SKY_PURPLE, spaceAfter=8))
    story.append(Spacer(1, 4))

    meta = [
        ["URL Assessed",        Paragraph(url, S["body"])],
        ["Page Title",          page_title or "—"],
        ["Generated On",        datetime.now().strftime("%Y-%m-%d %H:%M UTC")],
        ["Tool",                f"Axessia | axe-core {axe_version}"],
        ["Viewports Tested",    " · ".join(viewports)],
        ["WCAG Standard",       "WCAG 2.2 (Level A + AA)"],
        ["EAA Ready",           "YES" if eaa.get("eaa_ready") else "NO — Failures present"],
        ["EAA Risk",            eaa.get("risk_level", "—")],
        ["Automated Score",     f"{score.get('score', '—')}%"],
        ["Critical Failures",   str(eaa.get("failed_critical_count", 0))],
        ["Total Failures",      str(len(failures))],
        ["Manual Checks",       str(len(manual_items))],
    ]

    meta_table = Table(
        [[Paragraph(f"<b>{k}</b>", S["body"]), Paragraph(str(v), S["body"])] for k, v in meta],
        colWidths=[50*mm, 120*mm]
    )
    meta_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (0, -1), LIGHT_GRAY),
        ("GRID",        (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0),(-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Page screenshots
    if page_shot or mobile_shot:
        story.append(Paragraph("Page Screenshots", S["h2"]))
        shot_cells = []
        if page_shot:
            img = _screenshot_image(page_shot, max_width=85*mm, max_height=60*mm)
            if img:
                shot_cells.append([Paragraph("Desktop (1280px)", S["caption"]), img])
        if mobile_shot:
            img = _screenshot_image(mobile_shot, max_width=45*mm, max_height=60*mm)
            if img:
                shot_cells.append([Paragraph("Mobile (375px)", S["caption"]), img])
        if shot_cells:
            story.append(Table(shot_cells, colWidths=[90*mm, 80*mm]))
        story.append(Spacer(1, 6))

    story.append(Paragraph(
        "This report presents accessibility findings using automated scanning (axe-core), "
        "assisted analysis, and manual verification requirements. Screenshots are provided "
        "as evidence for each failing element.",
        S["body"]
    ))
    story.append(PageBreak())

    # ════════════════════════════════════════════════
    # EXECUTIVE SUMMARY
    # ════════════════════════════════════════════════
    story.append(Paragraph("Executive Summary", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SKY_MAGENTA, spaceAfter=6))

    # Score table
    sev_counts = {}
    for r in failures:
        sev = r.get("severity", "moderate")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1

    summary_data = [
        [Paragraph("<b>Metric</b>", S["body"]), Paragraph("<b>Value</b>", S["body"])],
        ["Automated Score",          f"{score.get('score', '—')}%"],
        ["EAA Status",               "READY" if eaa.get("eaa_ready") else "NOT READY"],
        ["EAA Risk Level",           eaa.get("risk_level", "—")],
        ["Critical failures",        str(sev_counts.get("critical", 0))],
        ["Serious failures",         str(sev_counts.get("serious", 0))],
        ["Moderate failures",        str(sev_counts.get("moderate", 0))],
        ["Minor failures",           str(sev_counts.get("minor", 0))],
        ["Total failing instances",  str(score.get("total_instances", 0))],
        ["Automated rules passed",   str(len(passed))],
        ["Manual checks required",   str(len(manual_items))],
    ]

    sum_table = Table(
        [[Paragraph(str(r[0]), S["body"]), Paragraph(str(r[1]), S["body"])] for r in summary_data],
        colWidths=[80*mm, 90*mm]
    )
    sum_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), SKY_PURPLE),
        ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
        ("GRID",        (0, 0), (-1, -1), 0.5, BORDER_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1, -1), 4),
    ]))
    story.append(sum_table)
    story.append(Spacer(1, 6))

    # Blocking WCAG
    if eaa.get("blocking_wcag"):
        story.append(Paragraph("<b>EAA Blocking Criteria:</b>", S["body"]))
        story.append(Paragraph(", ".join(eaa["blocking_wcag"]), S["body"]))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ════════════════════════════════════════════════
    # FAILURES — DETAILED EVIDENCE
    # ════════════════════════════════════════════════
    if failures:
        story.append(Paragraph("Accessibility Failures — Evidence & Remediation", S["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=SKY_MAGENTA, spaceAfter=6))

        # Sort: critical first, then by instance count desc
        sev_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        failures_sorted = sorted(
            failures,
            key=lambda r: (sev_order.get(r.get("severity"), 4), -r.get("instance_count", 0))
        )

        for i, rule in enumerate(failures_sorted, 1):
            ai    = rule.get("ai_explanation") or {}
            insts = rule.get("instances", [])
            sev   = rule.get("severity", "moderate")

            # Rule header
            header_block = [
                Paragraph(f"<b>{i}. {rule['name']}</b>", S["h2"]),
                Paragraph(
                    f"WCAG {rule.get('wcag','—')} | Level {rule.get('level','—')} | "
                    f"{_severity_badge(sev)} | {rule.get('instance_count', 0)} instance(s) | "
                    f"Viewport: {rule.get('viewport','desktop')}",
                    S["body"]
                ),
            ]

            # Contrast ratio if available
            contrast = rule.get("contrast_ratio")
            if contrast:
                header_block.append(Paragraph(
                    f"<b>Contrast ratio:</b> {contrast.get('actual','—')}:1 "
                    f"(Required: {contrast.get('required','4.5')}:1) | "
                    f"FG: {contrast.get('fg_color','—')} | BG: {contrast.get('bg_color','—')}",
                    S["body"]
                ))

            story.append(KeepTogether(header_block))
            story.append(Spacer(1, 3))

            # AI explanation
            if ai:
                ai_data = [
                    ["User Impact",  ai.get("user_impact", "—")],
                    ["Why It Matters", ai.get("why_it_matters", "—")],
                    ["Developer Action", ai.get("dev_action", "—")],
                    ["QA Steps",     "\n".join(ai.get("qa_steps", [])) if isinstance(ai.get("qa_steps"), list) else ai.get("qa_steps","—")],
                    ["EAA Context",  ai.get("eaa_context", "—")],
                ]
                ai_table = Table(
                    [[Paragraph(f"<b>{k}</b>", S["label"]), Paragraph(str(v), S["body"])] for k, v in ai_data],
                    colWidths=[38*mm, 132*mm]
                )
                ai_table.setStyle(TableStyle([
                    ("BACKGROUND",  (0, 0), (0, -1), LIGHT_GRAY),
                    ("GRID",        (0, 0), (-1, -1), 0.4, BORDER_GRAY),
                    ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                    ("FONTSIZE",    (0, 0), (-1, -1), 8.5),
                    ("TOPPADDING",  (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING",(0,0), (-1, -1), 3),
                ]))
                story.append(ai_table)
                story.append(Spacer(1, 4))

            # Failing instances with screenshots
            if insts:
                story.append(Paragraph("<b>Failing instances:</b>", S["body"]))

                for j, inst in enumerate(insts[:5], 1):
                    inst_items = []

                    # HTML snippet
                    snippet = inst.get("snippet", "")
                    if snippet:
                        inst_items.append(Paragraph(f"Instance {j} — HTML:", S["caption"]))
                        # Truncate long snippets
                        display_snippet = snippet[:300] + ("…" if len(snippet) > 300 else "")
                        inst_items.append(Paragraph(
                            display_snippet.replace("<", "&lt;").replace(">", "&gt;"),
                            S["mono"]
                        ))

                    # Failure summary
                    fail_summary = inst.get("failure_summary", "")
                    if fail_summary:
                        inst_items.append(Paragraph(
                            f"<i>Issue: {fail_summary}</i>",
                            S["caption"]
                        ))

                    # Screenshot
                    b64 = inst.get("screenshot_b64")
                    img = _screenshot_image(b64, max_width=150*mm, max_height=70*mm)
                    if img:
                        inst_items.append(Paragraph(f"Screenshot — Instance {j}:", S["caption"]))
                        inst_items.append(img)

                    if inst_items:
                        story.append(KeepTogether(inst_items + [Spacer(1, 4)]))

            # Help URL
            help_url = rule.get("help_url", "")
            if help_url:
                story.append(Paragraph(f"Reference: {help_url}", S["caption"]))

            story.append(HRFlowable(width="100%", thickness=0.4, color=BORDER_GRAY, spaceAfter=6))

        story.append(PageBreak())

    # ════════════════════════════════════════════════
    # MANUAL & ASSISTED CHECKS
    # ════════════════════════════════════════════════
    if manual_items:
        story.append(Paragraph("Manual & Assisted Verification Required", S["h1"]))
        story.append(HRFlowable(width="100%", thickness=1, color=SKY_MAGENTA, spaceAfter=6))
        story.append(Paragraph(
            "The following checks require human verification. Automated tools cannot "
            "reliably determine pass or fail for these criteria.",
            S["body"]
        ))
        story.append(Spacer(1, 6))

        manual_rows = [[
            Paragraph("<b>Rule</b>", S["body"]),
            Paragraph("<b>WCAG</b>", S["body"]),
            Paragraph("<b>Type</b>", S["body"]),
            Paragraph("<b>Severity</b>", S["body"]),
            Paragraph("<b>What to verify</b>", S["body"]),
        ]]

        for r in manual_items:
            ai    = r.get("ai_explanation") or {}
            steps = ai.get("qa_steps", [])
            manual_text = (
                "\n".join(steps) if isinstance(steps, list)
                else r.get("manual_remaining", "Manual verification required.")
            )
            manual_rows.append([
                Paragraph(r.get("name", ""), S["body"]),
                r.get("wcag", "—"),
                r.get("test_type", "").capitalize(),
                Paragraph(_severity_badge(r.get("severity","moderate")), S["body"]),
                Paragraph(manual_text[:200], S["body"]),
            ])

        man_table = Table(manual_rows, colWidths=[42*mm, 14*mm, 16*mm, 16*mm, 82*mm])
        man_table.setStyle(TableStyle([
            ("BACKGROUND",  (0, 0), (-1, 0), SKY_PURPLE),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("GRID",        (0, 0), (-1, -1), 0.4, BORDER_GRAY),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
            ("VALIGN",      (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE",    (0, 0), (-1, -1), 8),
            ("TOPPADDING",  (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ]))
        story.append(man_table)
        story.append(PageBreak())

    # ════════════════════════════════════════════════
    # FULL WCAG AUDIT TABLE
    # ════════════════════════════════════════════════
    story.append(Paragraph("Full WCAG Audit Table", S["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SKY_MAGENTA, spaceAfter=6))

    audit_rows = [[
        Paragraph("<b>Rule</b>", S["body"]),
        Paragraph("<b>WCAG</b>", S["body"]),
        Paragraph("<b>Level</b>", S["body"]),
        Paragraph("<b>Type</b>", S["body"]),
        Paragraph("<b>Status</b>", S["body"]),
        Paragraph("<b>Instances</b>", S["body"]),
    ]]

    auto_rules = [r for r in rules if r.get("test_type") == "automated"]
    for r in sorted(auto_rules, key=lambda x: (x.get("wcag","z"), x.get("name",""))):
        audit_rows.append([
            Paragraph(r.get("name", "")[:60], S["body"]),
            r.get("wcag", "—"),
            r.get("level", "—"),
            r.get("test_type","").capitalize(),
            Paragraph(_status_badge(r.get("status","")), S["body"]),
            str(r.get("instance_count", 0)) if r.get("status") == "fail" else "—",
        ])

    audit_table = Table(audit_rows, colWidths=[64*mm, 14*mm, 12*mm, 16*mm, 14*mm, 16*mm])
    audit_table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0), SKY_PURPLE),
        ("TEXTCOLOR",      (0, 0), (-1, 0), colors.white),
        ("GRID",           (0, 0), (-1, -1), 0.4, BORDER_GRAY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 8))

    # ── Footer ──────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=SKY_PURPLE, spaceAfter=4))
    story.append(Paragraph(
        f"Generated by Axessia Accessibility Intelligence | "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')} | "
        f"axe-core {axe_version} | WCAG 2.2 AA | EAA / EN 301 549",
        S["caption"]
    ))

    doc.build(story)
    return buffer.getvalue()
