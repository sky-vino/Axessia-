# app_msa.py
import streamlit as st
import uuid

from mobile.android_worker import run_android_scan
from mobile.screen_fingerprint import compute_screen_signature
from ai_mobile_explainer import get_mobile_ai_explanation
from eaa_scoring import compute_eaa_score, compute_eaa_risk
from pdf_report import generate_pdf_report


# =================================================
# SESSION STATE
# =================================================
if "msa_view" not in st.session_state:
    st.session_state.msa_view = "dashboard"   # dashboard | screen_list | screen_details

if "msa_results" not in st.session_state:
    st.session_state.msa_results = None

if "msa_expected_screens" not in st.session_state:
    st.session_state.msa_expected_screens = 1

if "msa_active_screen_id" not in st.session_state:
    st.session_state.msa_active_screen_id = None


# =================================================
# DASHBOARD
# =================================================
if st.session_state.msa_view == "dashboard":

    st.subheader("📱 MSA – Mobile Scan Assistant (Android)")

    with st.container(border=True):
        app_package = st.text_input(
            "Android App Package Name",
            placeholder="e.g. cris.org.in.prs.ima"
        )

        expected = st.number_input(
            "Expected number of screens",
            min_value=1,
            value=1,
            help="Used only for coverage transparency"
        )

        if st.button("Run Scan on Current Screen", type="primary") and app_package:
            with st.spinner("Capturing current screen…"):
                result = run_android_scan(
                    app_package=app_package,
                    assistive_context={}
                )

            screen = result["screens"][0]
            screen["id"] = str(uuid.uuid4())
            screen["name"] = "Screen 1"
            screen["signature"] = compute_screen_signature(screen)

            st.session_state.msa_results = {
                "app_package": app_package,
                "platform": "android",
                "screens": [screen],
            }
            st.session_state.msa_expected_screens = expected
            st.session_state.msa_view = "screen_list"
            st.rerun()


# =================================================
# SCREEN LIST (LIKE WSC URL LIST)
# =================================================
elif st.session_state.msa_view == "screen_list":

    res = st.session_state.msa_results
    screens = res["screens"]

    # ---- App-level EAA ----
    all_rules = []
    for s in screens:
        all_rules.extend(s["rules"])

    eaa_score = compute_eaa_score(all_rules)
    eaa_risk = compute_eaa_risk(eaa_score)

    st.subheader(f"Results – {res['app_package']}")

    # ---- Metrics ----
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("EAA Score", f"{eaa_score:.1f}")
        c2.metric("EAA Risk", eaa_risk)
        c3.metric("Screens Scanned", len(screens))

    # ---- Coverage ----
    scanned = len(screens)
    expected = st.session_state.msa_expected_screens
    coverage = int((scanned / expected) * 100) if expected else 0

    st.markdown("### 📊 Screen Coverage")
    st.progress(min(coverage, 100))
    st.write(f"{scanned} / {expected} screens scanned ({coverage}%)")

    st.divider()
    st.markdown("## Screens")

    # ---- Screen cards ----
    for screen in screens:
        with st.container(border=True):
            st.markdown(f"### {screen['name']}")
            st.write(f"Risk: **{screen['risk'].upper()}**")

            c1, c2 = st.columns(2)

            if c1.button("View Results", key=f"view_{screen['id']}"):
                st.session_state.msa_active_screen_id = screen["id"]
                st.session_state.msa_view = "screen_details"
                st.rerun()

            c2.download_button(
                "Export PDF",
                data=generate_pdf_report(
                    f"{res['app_package']} – {screen['name']}",
                    {"rules": screen["rules"]}
                ),
                file_name=f"axessia_mobile_{res['app_package']}_{screen['name'].replace(' ','_')}.pdf",
                mime="application/pdf",
            )

    # ---- Add Screen ----
    with st.expander("➕ Add Screen"):
        st.info("Navigate to a DIFFERENT screen in the app, then capture it.")

        new_name = st.text_input("Screen name")

        if st.button("Capture This Screen") and new_name:
            with st.spinner("Capturing screen…"):
                new_result = run_android_scan(
                    app_package=res["app_package"],
                    assistive_context={}
                )

            new_screen = new_result["screens"][0]
            new_signature = compute_screen_signature(new_screen)

            if any(s["signature"] == new_signature for s in screens):
                st.warning(
                    "⚠️ This screen appears identical to a previously scanned screen.\n"
                    "Please navigate to a different screen and try again."
                )
            else:
                new_screen["id"] = str(uuid.uuid4())
                new_screen["name"] = new_name
                new_screen["signature"] = new_signature
                screens.append(new_screen)
                st.success(f"Screen '{new_name}' added.")
                st.rerun()


# =================================================
# SCREEN DETAILS (FULL RESTORED VIEW)
# =================================================
else:
    res = st.session_state.msa_results
    screens = res["screens"]

    active = next(
        s for s in screens
        if s["id"] == st.session_state.msa_active_screen_id
    )

    st.subheader(f"{res['app_package']} → {active['name']}")

    if st.button("← Back to Screens"):
        st.session_state.msa_view = "screen_list"
        st.rerun()

    tabs = st.tabs([
        "Issues",
        "AI Explanation",
        "Manual & Assisted",
        "EAA Context"
    ])

    # ---------------- ISSUES ----------------
    with tabs[0]:
        any_fail = False
        for r in active["rules"]:
            if r["test_type"] == "automated" and r["status"] == "fail":
                any_fail = True
                with st.expander(f"❌ {r['name']} ({r['wcag']})"):
                    st.write(f"Severity: **{r['severity']}**")
                    if r.get("instances"):
                        st.json(r["instances"])
        if not any_fail:
            st.success("No automated failures detected on this screen.")

    # ---------------- AI EXPLANATION ----------------
    with tabs[1]:
        explained = False
        for r in active["rules"]:
            if r["status"] != "fail":
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

    # ---------------- MANUAL & ASSISTED ----------------
    with tabs[2]:
        shown = False
        for r in active["rules"]:
            if r["test_type"] in ("assisted", "manual"):
                shown = True
                with st.expander(f"🟠 {r['name']} ({r['wcag']})"):
                    if r.get("automated_assist"):
                        st.info(r["automated_assist"])
                    if r.get("manual_remaining"):
                        st.warning(r["manual_remaining"])
        if not shown:
            st.success("No assisted or manual checks pending for this screen.")

    # ---------------- EAA CONTEXT ----------------
    with tabs[3]:
        screen_score = compute_eaa_score(active["rules"])
        screen_risk = compute_eaa_risk(screen_score)

        st.metric("Screen EAA Score", f"{screen_score:.1f}")
        st.metric("Screen EAA Risk", screen_risk)

        st.write(
            "EAA score reflects the combined impact of automated failures, "
            "assisted gaps, and manual verification requirements for this screen."
        )
