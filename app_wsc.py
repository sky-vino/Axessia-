import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from pdf_report import generate_pdf_report

# ================= CONFIG =================
API_URL = os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan")
API_KEY = os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")

SEVERITY_WEIGHTS = {
    "critical": 4,
    "serious": 3,
    "moderate": 2,
    "minor": 1,
}

CONFIDENCE_LABELS = {
    "automated": "🟢 Automated",
    "assisted": "🟠 Assisted",
    "manual": "🔴 Manual",
}

# ================= UTILS =================
def safe_ai(val):
    return val if isinstance(val, dict) else {}

def calculate_score(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    df = df.copy()
    df["weight"] = df["severity"].map(SEVERITY_WEIGHTS).fillna(0)
    max_score = len(df) * max(SEVERITY_WEIGHTS.values())
    passed_score = df[df["status"] == "pass"]["weight"].sum()
    return round((passed_score / max_score) * 100, 1) if max_score else 0.0

def call_secure_scan(url: str):
    try:
        response = requests.post(
            API_URL,
            headers={
                "Content-Type": "application/json",
                "x-api-key": API_KEY,
            },
            json={"url": url},
            timeout=60,
        )

        if response.status_code == 401:
            st.error("Unauthorized. Invalid API key.")
            return None

        if response.status_code == 429:
            st.warning("Rate limit exceeded. Please wait and try again.")
            return None

        if response.status_code >= 500:
            st.error("Server error during scan.")
            return None

        return response.json()

    except requests.exceptions.Timeout:
        st.error("Scan timed out.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to API server.")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

# ================= SESSION STATE =================
if "view" not in st.session_state:
    st.session_state.view = "dashboard"
if "active_url" not in st.session_state:
    st.session_state.active_url = None
if "scan_results" not in st.session_state:
    st.session_state.scan_results = {}
if "show_add_url" not in st.session_state:
    st.session_state.show_add_url = False


# ======================================================
# DASHBOARD VIEW
# ======================================================
if st.session_state.view == "dashboard":

    h1, h2 = st.columns([6, 1])
    h1.subheader("Scan Results")
    if h2.button("➕ Add URL"):
        st.session_state.show_add_url = not st.session_state.show_add_url

    if st.session_state.show_add_url:
        with st.container(border=True):
            url = st.text_input("Enter URL")
            if st.button("Run Scan", type="primary"):
                if url.strip():
                    with st.spinner("Running scan…"):
                        result = call_secure_scan(url.strip())
                        if result:
                            st.session_state.scan_results[url.strip()] = result
                            st.session_state.show_add_url = False
                            st.rerun()
                else:
                    st.warning("Please enter a valid URL")

    if not st.session_state.scan_results:
        st.info("No scans yet. Add a URL to begin.")
        st.stop()

    # Dashboard charts
    all_rules = []
    for d in st.session_state.scan_results.values():
        if "rules" in d:
            all_rules.extend(d["rules"])

    if all_rules:
        df_all = pd.DataFrame(all_rules)
        c1, c2 = st.columns(2)

        with c1:
            st.plotly_chart(
                px.pie(
                    df_all.groupby("severity").size().reset_index(name="count"),
                    names="severity",
                    values="count",
                    hole=0.4,
                    title="Severity Distribution",
                ),
                use_container_width=True,
            )

        with c2:
            scores = []
            for u, d in st.session_state.scan_results.items():
                scores.append({
                    "URL": u,
                    "Score": calculate_score(pd.DataFrame(d.get("rules", [])))
                })
            st.plotly_chart(
                px.bar(pd.DataFrame(scores), x="URL", y="Score", title="Score per URL"),
                use_container_width=True,
            )

    st.divider()

    for url, result in st.session_state.scan_results.items():
        with st.container(border=True):
            st.markdown(f"### {url}")

            if "rules" not in result:
                st.error("Scan failed")
                continue

            df = pd.DataFrame(result["rules"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Score", f"{calculate_score(df)}%")
            c2.metric("Failures", len(df[df["status"] == "fail"]))
            c3.metric("Passed", len(df[df["status"] == "pass"]))
            c4.metric("Needs Review", len(df[df["status"].isin(["manual", "assisted"])]))

            a1, a2 = st.columns(2)
            if a1.button("View Results", key=f"view_{url}"):
                st.session_state.active_url = url
                st.session_state.view = "results"
                st.rerun()

            a2.download_button(
                "Export PDF",
                data=generate_pdf_report(url, result),
                file_name=f"axessia_{url.replace('https://','').replace('/','_')}.pdf",
                mime="application/pdf",
            )

# ======================================================
# RESULTS VIEW (FULL ORIGINAL RESTORED)
# ======================================================
if st.session_state.view == "results":

    url = st.session_state.active_url
    data = st.session_state.scan_results.get(url)

    if not data or "rules" not in data:
        st.error("No results available.")
        st.stop()

    df = pd.DataFrame(data["rules"])

    if st.button("← Back to Dashboard"):
        st.session_state.view = "dashboard"
        st.session_state.active_url = None
        st.rerun()

    st.markdown(f"## Results for `{url}`")

    tabs = st.tabs([
        "Overview",
        "WCAG",
        "Issues",
        "Manual & Assisted",
        "AI Agent – Dev",
        "AI Agent – QA",
        "EAA Readiness",
    ])

    # ---------------- OVERVIEW ----------------
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Failures", len(df[df["status"] == "fail"]))
        c2.metric("Passed", len(df[df["status"] == "pass"]))
        c3.metric("Needs Review", len(df[df["status"].isin(["manual","assisted"])]))
        c4.metric("Total Rules", len(df))

        st.metric("Severity-Weighted Accessibility Score", f"{calculate_score(df)}%")

        st.plotly_chart(
            px.pie(
                df.groupby("severity").size().reset_index(name="count"),
                names="severity",
                values="count",
                hole=0.5,
            ),
            use_container_width=True,
        )

        st.plotly_chart(
            px.density_heatmap(
                df,
                x="wcag",
                y="severity",
                title="Severity × WCAG Heatmap",
            ),
            use_container_width=True,
        )

    # ---------------- WCAG ----------------
    with tabs[1]:
        t = df.copy()
        t["Confidence"] = t["test_type"].map(CONFIDENCE_LABELS)
        st.dataframe(
            t[["name","wcag","level","severity","status","Confidence"]],
            use_container_width=True,
            hide_index=True,
        )

    # ---------------- ISSUES ----------------
    with tabs[2]:
        for i, r in df[df["status"]=="fail"].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"🔴 {r['name']} (WCAG {r['wcag']}, Severity {r['severity']})"):
                if ai.get("why_not_automated"):
                    st.write("**Why this fails**")
                    st.write(ai["why_not_automated"])
                if ai.get("who_is_impacted"):
                    st.write("**Who is impacted**")
                    st.write(ai["who_is_impacted"])
                if ai.get("legal_risk"):
                    st.write("**Legal / Compliance Risk**")
                    st.write(ai["legal_risk"])
                if ai.get("what_to_test_manually"):
                    st.write("**How to Fix (Developer Action)**")
                    st.write(ai["what_to_test_manually"])
                st.button("🧾 Create Defect", key=f"defect_{i}")

    # ---------------- MANUAL & ASSISTED ----------------
    with tabs[3]:
        for _, r in df[df["status"].isin(["manual","assisted"])].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"{CONFIDENCE_LABELS[r['test_type']]} {r['name']} (WCAG {r['wcag']})"):
                if ai.get("why_not_automated"):
                    st.write("**Why manual testing is required**")
                    st.write(ai["why_not_automated"])
                if ai.get("what_to_test_manually"):
                    st.write("**What QA must verify**")
                    st.write(ai["what_to_test_manually"])
                if ai.get("qa_validation_steps"):
                    st.write("**QA Validation Steps**")
                    for step in ai["qa_validation_steps"]:
                        st.write(f"- {step}")

    # ---------------- AI AGENT – DEV ----------------
    with tabs[4]:
        for _, r in df[df["status"]=="fail"].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"Fix: {r['name']}"):
                if r.get("instances"):
                    st.code(r["instances"][0].get("snippet",""), language="html")
                if ai.get("what_to_test_manually"):
                    st.write(ai["what_to_test_manually"])

    # ---------------- AI AGENT – QA ----------------
    with tabs[5]:
        rows=[]
        for _, r in df[df["status"].isin(["manual","assisted"])].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            rows.append({
                "Rule": r["name"],
                "WCAG": r["wcag"],
                "Severity": r["severity"],
                "Confidence": CONFIDENCE_LABELS[r["test_type"]],
                "Test Steps": " → ".join(ai.get("qa_validation_steps",[]))
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # ---------------- EAA READINESS ----------------
    with tabs[6]:
        high = df[
            (df["level"].isin(["A","AA"])) &
            (df["severity"].isin(["critical","serious"])) &
            (df["status"]!="pass")
        ]

        if not high.empty:
            st.error("🔴 High EAA Risk")
        else:
            st.success("🟢 Low EAA Risk")

        for _, r in high.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            if ai.get("legal_risk"):
                with st.expander(f"{r['name']} (WCAG {r['wcag']})"):
                    st.write(ai["legal_risk"])