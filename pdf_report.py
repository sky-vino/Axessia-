from io import BytesIO
from datetime import datetime
import pandas as pd

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors


def generate_pdf_report(url: str, scan_data: dict) -> bytes:
    """
    Generates an auditor-ready Axessia accessibility report for ONE URL.
    """

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    story = []

    rules = scan_data.get("rules", [])
    df = pd.DataFrame(rules)

    # =====================================================
    # 1. COVER PAGE
    # =====================================================
    story.append(Paragraph("Axessia – Accessibility Assessment Report", styles["Title"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(f"<b>URL Assessed:</b> {url}", styles["Normal"]))
    story.append(Paragraph(
        f"<b>Generated On:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"],
    ))
    story.append(Spacer(1, 24))
    story.append(Paragraph(
        "This report presents the accessibility findings identified by Axessia using a "
        "combination of automated testing, assisted analysis, and manual verification requirements.",
        styles["Normal"],
    ))
    story.append(PageBreak())

    # =====================================================
    # 2. EXECUTIVE SUMMARY
    # =====================================================
    failures = len(df[df["status"] == "fail"])
    passed = len(df[df["status"] == "pass"])
    needs_review = len(df[df["status"].isin(["manual", "assisted"])])
    total = len(df)

    story.append(Paragraph("Executive Summary", styles["Heading1"]))
    story.append(Spacer(1, 12))

    summary_table = Table(
        [
            ["Total Rules Evaluated", total],
            ["Failures", failures],
            ["Passed", passed],
            ["Needs Review", needs_review],
        ],
        colWidths=[250, 150],
    )

    summary_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
    ]))

    story.append(summary_table)
    story.append(PageBreak())

    # =====================================================
    # 3. SCOPE & METHODOLOGY
    # =====================================================
    story.append(Paragraph("Scope & Methodology", styles["Heading1"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        "Axessia evaluates accessibility conformance using the following methods:",
        styles["Normal"],
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "• <b>Automated checks</b> powered by axe-core for detectable WCAG failures.<br/>"
        "• <b>Assisted analysis</b> where automation is insufficient and AI guidance is provided.<br/>"
        "• <b>Manual verification</b> where human testing is required for compliance assurance.",
        styles["Normal"],
    ))

    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "This assessment is limited to the specific URL listed above. "
        "No additional pages or authenticated areas were included unless explicitly stated.",
        styles["Normal"],
    ))
    story.append(PageBreak())

    # =====================================================
    # 4. WCAG COMPLIANCE SUMMARY
    # =====================================================
    story.append(Paragraph("WCAG Compliance Summary", styles["Heading1"]))
    story.append(Spacer(1, 12))

    wcag_rows = [["Rule", "WCAG SC", "Severity", "Status", "Confidence"]]
    for _, row in df.iterrows():
        wcag_rows.append([
            row.get("name"),
            row.get("wcag") or "—",
            row.get("severity"),
            row.get("status"),
            row.get("test_type"),
        ])

    wcag_table = Table(wcag_rows, repeatRows=1, colWidths=[160, 60, 60, 60, 80])
    wcag_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))

    story.append(wcag_table)
    story.append(PageBreak())

    # =====================================================
    # 5. ACCESSIBILITY ISSUES (FAILURES)
    # =====================================================
    story.append(Paragraph("Accessibility Issues", styles["Heading1"]))
    story.append(Spacer(1, 12))

    for _, row in df[df["status"] == "fail"].iterrows():
        ai = row.get("ai_explanation")
        story.append(Paragraph(
            f"<b>{row.get('name')}</b> (WCAG {row.get('wcag')})",
            styles["Heading3"],
        ))
        story.append(Paragraph(
            f"Severity: {row.get('severity')} | Confidence: {row.get('test_type')}",
            styles["Normal"],
        ))

        if isinstance(ai, dict):
            if ai.get("why_not_automated"):
                story.append(Paragraph(f"<b>Why this fails:</b> {ai['why_not_automated']}", styles["Normal"]))
            if ai.get("who_is_impacted"):
                story.append(Paragraph(f"<b>Who is impacted:</b> {ai['who_is_impacted']}", styles["Normal"]))
            if ai.get("legal_risk"):
                story.append(Paragraph(f"<b>Legal / Compliance Risk:</b> {ai['legal_risk']}", styles["Normal"]))
            if ai.get("what_to_test_manually"):
                story.append(Paragraph(f"<b>How to fix:</b> {ai['what_to_test_manually']}", styles["Normal"]))

        story.append(Spacer(1, 12))

    story.append(PageBreak())

    # =====================================================
    # 6. MANUAL & ASSISTED VERIFICATION
    # =====================================================
    story.append(Paragraph("Manual & Assisted Verification", styles["Heading1"]))
    story.append(Spacer(1, 12))

    for _, row in df[df["status"].isin(["manual", "assisted"])].iterrows():
        ai = row.get("ai_explanation")
        story.append(Paragraph(
            f"<b>{row.get('name')}</b> (WCAG {row.get('wcag')})",
            styles["Heading3"],
        ))

        if isinstance(ai, dict):
            if ai.get("why_not_automated"):
                story.append(Paragraph(f"<b>Why manual review is required:</b> {ai['why_not_automated']}", styles["Normal"]))
            if ai.get("qa_validation_steps"):
                story.append(Paragraph(
                    "<b>QA Validation Steps:</b> " + ", ".join(ai["qa_validation_steps"]),
                    styles["Normal"],
                ))

        story.append(Spacer(1, 12))

    story.append(PageBreak())

    # =====================================================
    # 7. EAA READINESS
    # =====================================================
    story.append(Paragraph("EAA Readiness Assessment", styles["Heading1"]))
    story.append(Spacer(1, 12))

    high_risk = df[
        (df["level"].isin(["A", "AA"])) &
        (df["severity"].isin(["critical", "serious"])) &
        (df["status"] != "pass")
    ]

    if not high_risk.empty:
        story.append(Paragraph(
            "This page presents <b>high-risk accessibility issues</b> that may impact "
            "compliance with the European Accessibility Act (EAA).",
            styles["Normal"],
        ))
    else:
        story.append(Paragraph(
            "No high-risk WCAG A or AA failures were detected for this URL.",
            styles["Normal"],
        ))

    for _, row in high_risk.iterrows():
        ai = row.get("ai_explanation")
        if isinstance(ai, dict) and ai.get("legal_risk"):
            story.append(Paragraph(
                f"<b>{row.get('name')}</b>: {ai['legal_risk']}",
                styles["Normal"],
            ))

    story.append(PageBreak())

    # =====================================================
    # BUILD PDF
    # =====================================================
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
