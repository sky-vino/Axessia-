import streamlit as st
import uuid

from ai_mobile_explainer import get_mobile_ai_explanation
from eaa_scoring import compute_eaa_score, compute_eaa_risk
from pdf_report import generate_pdf_report


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


# ✅ DEMO MODE RESULTS (NO BACKEND NEEDED)
def fetch_mobile_results(session_id: str):
    return {
        "app_package": "it.overit.mobile.skybbhres",
        "screens": [
            {
                "id": "1",
                "name": "Home Screen",
                "risk": "high",
                "rules": [
                    {
                        "id": "img-alt",
                        "name": "Image missing alt text",
                        "wcag": "1.1.1",
                        "severity": "high",
                        "status": "fail",
                        "test_type": "automated",
                        "instances": [{"element": "ImageView"}]
                    }
                ]
            },
            {
                "id": "2",
                "name": "Login Screen",
                "risk": "medium",
                "rules": [
                    {
                        "id": "label",
                        "name": "Input missing label",
                        "wcag": "3.3.2",
                        "severity": "medium",
                        "status": "fail",
                        "test_type": "automated",
                        "instances": [{"element": "EditText"}]
                    }
                ]
            }
        ]
    }


# ======================================================
# DASHBOARD
# ======================================================
if st.session_state.msa_view == "dashboard":

    st.subheader("📱 MSA – Mobile Scan Assistant (Android)")

    with st.container(border=True):
        st.markdown("**How Android scanning works:**")
        st.markdown(
            "1. Enter app package + session name below and click **Start Session**\n"
            "2. Run the local scanner (ADB-based)\n"
            "3. Click **Check for Results**\n"
        )

    st.divider()

    # Start new session
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
                value=2,
            )

            if st.button("▶️ Start Session", type="primary"):
                if not app_package.strip():
                    st.error("Please enter an app package name.")
                else:
                    session_id = str(uuid.uuid4())[:8].upper()
                    st.session_state.msa_session_id = session_id
                    st.session_state.msa_expected_screens = expected
                    st.session_state["msa_pkg"] = app_package.strip()
                    st.rerun()

    # Active session
    else:
        session_id = st.session_state.msa_session_id
        app_package = st.session_state.get("msa_pkg", "Unknown")

        st.success("✅ Session active — demo mode")

        col1, col2 = st.columns([2, 1])

        with col1:
            if st.button("🔄 Check for Results", type="primary"):
                results = fetch_mobile_results(session_id)
                st.session_state.msa_results = results
                st.session_state.msa_view = "screen_list"
                st.rerun()

        with col2:
            if st.button("↩️ New Session"):
                st.session_state.msa_session_id = None
                st.session_state.msa_results = None
                st.rerun()


# ======================================================
# SCREEN LIST
# ======================================================
elif st.session_state.msa_view == "screen_list":

    res = st.session_state.msa_results
    screens = res["screens"]

    all_rules = []
    for s in screens:
        all_rules.extend(s["rules"])

    eaa_score = compute_eaa_score(all_rules)
    eaa_risk = compute_eaa_risk(eaa_score)

    st.subheader(f"Results – {res.get('app_package')}")

    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.metric("EAA Score", f"{eaa_score:.1f}")
        c2.metric("EAA Risk", eaa_risk)
        c3.metric("Screens", len(screens))

    st.divider()

    for screen in screens:
        with st.container(border=True):
            st.markdown(f"### {screen['name']}")
            st.write(f"Risk: **{screen['risk'].upper()}**")

            if st.button("View Results", key=screen["id"]):
                st.session_state.msa_active_screen_id = screen["id"]
                st.session_state.msa_view = "screen_details"
                st.rerun()

    if st.button("↩️ Back"):
        st.session_state.msa_view = "dashboard"
        st.rerun()


# ======================================================
# SCREEN DETAILS
# ======================================================
else:
    res = st.session_state.msa_results
    screens = res["screens"]

    active = next(
        (s for s in screens if s["id"] == st.session_state.msa_active_screen_id),
        None,
    )

    st.subheader(f"{res['app_package']} → {active['name']}")

    if st.button("← Back"):
        st.session_state.msa_view = "screen_list"
        st.rerun()

    for r in active["rules"]:
        with st.expander(f"❌ {r['name']} ({r['wcag']})"):
            st.write(f"Severity: **{r['severity']}**")
            st.json(r["instances"])

            explanation = get_mobile_ai_explanation(r["id"])
            if explanation:
                st.markdown("### 🧠 AI Explanation")
                st.write(explanation["user_impact"])