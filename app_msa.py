# ======================================================
# AXESSIA – MSA Android (Azure Edition)
#
# ADB scanning runs on your LOCAL machine (device connected via USB).
# This UI receives and displays results sent from the local runner.
#
# Workflow:
#   1. Enter app package + session name here → note the Session ID
#   2. On your laptop: python local_mobile_runner.py --session <ID>
#   3. Results appear here automatically
# ======================================================

import streamlit as st
import requests
import os
import uuid

from ai_mobile_explainer import get_mobile_ai_explanation
from eaa_scoring import compute_eaa_score, compute_eaa_risk
from pdf_report import generate_pdf_report

API_BASE = os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan").replace("/scan", "")
API_KEY  = os.getenv("AXESSIA_API_KEY", "super-secret-demo-key")


# ── Session state ──────────────────────────────────────
if "msa_view" not in st.session_state:
    st.session_state.msa_view = "dashboard"

if "msa_results" not in st.session_state:
    st.session_state.msa_results = None

if "msa_session_id" not in st.session_state:
    st.session_state.msa_session_id = None

if "msa_expected_screens" not in st.session_state:
    st.session_state.msa_expected_screens = 1

if "msa_active_screen_id" not in st.session_state:
    st.session_state.msa_active_screen_id = None


def fetch_mobile_results(session_id: str) -> dict | None:
    """Poll Azure API for results sent by the local runner."""
    try:
        resp = requests.get(
            f"{API_BASE}/mobile-results/{session_id}",
            headers={"x-api-key": API_KEY},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data if data.get("screens") else None
        return None
    except Exception:
        return None


# ======================================================
# DASHBOARD
# ======================================================
if st.session_state.msa_view == "dashboard":

    st.subheader("📱 MSA – Mobile Scan Assistant (Android)")

    # ── How it works callout ───────────────────────────
    with st.container(border=True):
        st.markdown("**How Android scanning works from Azure:**")
        st.markdown(
            "1. Enter app package + session name below and click **Start Session**\n"
            "2. Copy the Session ID shown\n"
            "3. On your laptop (Android device connected via USB), run:\n"
        )
        st.code("python local_mobile_runner.py --session <SESSION_ID> --app <PACKAGE_NAME>")
        st.markdown("4. Click **🔄 Check for Results** once the local scan completes")

    st.divider()

    # ── New session form ───────────────────────────────
    if not st.session_state.msa_session_id:
        st.markdown("**Start a new scan session**")
        with st.container(border=True):
            app_package = st.text_input(
                "Android App Package Name",
                placeholder="e.g. com.sky.it",
                key="msa_pkg_input",
            )
            expected = st.number_input(
                "Expected number of screens",
                min_value=1,
                value=1,
                help="Used for coverage calculation",
            )
            if st.button("▶️ Start Session", type="primary", key="msa_start_btn"):
                if not app_package.strip():
                    st.error("Please enter an app package name.")
                else:
                    session_id = str(uuid.uuid4())[:8].upper()
                    st.session_state.msa_session_id      = session_id
                    st.session_state.msa_expected_screens = expected
                    st.session_state["msa_pkg"]          = app_package.strip()
                    st.rerun()

    # ── Active session — waiting for results ───────────
    else:
        session_id  = st.session_state.msa_session_id
        app_package = st.session_state.get("msa_pkg", "Unknown")

        st.success(f"✅ Session active — waiting for results from your local machine")

        with st.container(border=True):
            st.markdown("**Run this command on your laptop:**")
            st.code(
                f"python local_mobile_runner.py "
                f"--session {session_id} "
                f"--app {app_package} "
                f"--azure https://axessia-app.azurewebsites.net"
            )
            st.caption(f"Session ID: `{session_id}`  ·  Package: `{app_package}`")

        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("🔄 Check for Results", type="primary", key="msa_refresh_btn"):
                with st.spinner("Checking Azure for results…"):
                    results = fetch_mobile_results(session_id)
                if results:
                    st.session_state.msa_results = results
                    st.session_state.msa_view    = "screen_list"
                    st.rerun()
                else:
                    st.info("No results yet. Run the local scanner and try again.")
        with col2:
            if st.button("↩️ New Session", key="msa_new_btn"):
                st.session_state.msa_session_id = None
                st.session_state.msa_results    = None
                st.rerun()


# ======================================================
# SCREEN LIST
# ======================================================
elif st.session_state.msa_view == "screen_list":

    res     = st.session_state.msa_results
    screens = res["screens"]

    all_rules = []
    for s in screens:
        all_rules.extend(s["rules"])

    eaa_score = compute_eaa_score(all_rules)
    eaa_risk  = compute_eaa_risk(eaa_score)

    st.subheader(f"Results – {res.get('app_package', 'Android App')}")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("EAA Score",      f"{eaa_score:.1f}")
        c2.metric("EAA Risk",       eaa_risk)
        c3.metric("Screens Scanned", len(screens))

    scanned  = len(screens)
    expected = st.session_state.msa_expected_screens
    coverage = int((scanned / expected) * 100) if expected else 0

    st.markdown("### 📊 Screen Coverage")
    st.progress(min(coverage, 100))
    st.write(f"{scanned} / {expected} screens scanned ({coverage}%)")

    st.divider()
    st.markdown("## Screens")

    for screen in screens:
        with st.container(border=True):
            st.markdown(f"### {screen['name']}")
            st.write(f"Risk: **{screen.get('risk', 'unknown').upper()}**")

            c1, c2 = st.columns(2)
            if c1.button("View Results", key=f"view_{screen['id']}"):
                st.session_state.msa_active_screen_id = screen["id"]
                st.session_state.msa_view = "screen_details"
                st.rerun()

            c2.download_button(
                "Export PDF",
                data=generate_pdf_report(
                    f"{res.get('app_package', 'App')} – {screen['name']}",
                    {"rules": screen["rules"]},
                ),
                file_name=f"axessia_android_{screen['name'].replace(' ','_')}.pdf",
                mime="application/pdf",
                key=f"pdf_{screen['id']}",
            )

    if st.button("↩️ New Scan Session", key="msa_back_to_dash"):
        st.session_state.msa_session_id = None
        st.session_state.msa_results    = None
        st.session_state.msa_view       = "dashboard"
        st.rerun()


# ======================================================
# SCREEN DETAILS
# ======================================================
else:
    res     = st.session_state.msa_results
    screens = res["screens"]

    active = next(
        (s for s in screens if s["id"] == st.session_state.msa_active_screen_id),
        screens[0] if screens else None,
    )

    if not active:
        st.error("Screen not found.")
        st.stop()

    st.subheader(f"{res.get('app_package', 'App')} → {active['name']}")

    if st.button("← Back to Screens"):
        st.session_state.msa_view = "screen_list"
        st.rerun()

    tabs = st.tabs(["Issues", "AI Explanation", "Manual & Assisted", "EAA Context"])

    # ── Issues ─────────────────────────────────────────
    with tabs[0]:
        any_fail = False
        for r in active["rules"]:
            if r.get("test_type") == "automated" and r.get("status") == "fail":
                any_fail = True
                with st.expander(f"❌ {r['name']} ({r.get('wcag', '')})"):
                    st.write(f"Severity: **{r.get('severity', '')}**")
                    if r.get("instances"):
                        st.json(r["instances"])
        if not any_fail:
            st.success("No automated failures detected on this screen.")

    # ── AI Explanation ─────────────────────────────────
    with tabs[1]:
        explained = False
        for r in active["rules"]:
            if r.get("status") != "fail":
                continue
            explanation = get_mobile_ai_explanation(r["id"])
            if not explanation:
                continue
            explained = True
            with st.expander(f"🧠 {explanation['title']} ({explanation['wcag']})"):
                st.markdown("**User impact**")
                st.write(explanation["user_impact"])
                st.markdown("**Why this matters**")
                st.write(explanation["why_it_matters"])
                st.markdown("**For developers**")
                st.info(explanation["dev_notes"])
                st.markdown("**For QA**")
                st.warning(explanation["qa_notes"])
                st.markdown("**EAA context**")
                st.write(explanation["eaa_context"])
        if not explained:
            st.info("No AI explanations applicable for this screen.")

    # ── Manual & Assisted ──────────────────────────────
    with tabs[2]:
        shown = False
        for r in active["rules"]:
            if r.get("test_type") in ("assisted", "manual"):
                shown = True
                with st.expander(f"🟠 {r['name']} ({r.get('wcag', '')})"):
                    if r.get("automated_assist"):
                        st.info(r["automated_assist"])
                    if r.get("manual_remaining"):
                        st.warning(r["manual_remaining"])
        if not shown:
            st.success("No assisted or manual checks pending.")

    # ── EAA Context ────────────────────────────────────
    with tabs[3]:
        screen_score = compute_eaa_score(active["rules"])
        screen_risk  = compute_eaa_risk(screen_score)
        st.metric("Screen EAA Score", f"{screen_score:.1f}")
        st.metric("Screen EAA Risk",  screen_risk)
        st.write(
            "EAA score reflects the combined impact of automated failures, "
            "assisted gaps, and manual verification requirements."
        )
