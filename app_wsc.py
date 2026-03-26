import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from pdf_report import generate_pdf_report
from auth_flow import fully_automated_login, phase2_manual_otp, verify_session
from scanner_axe import run_scan_with_cookies

# ================= CONFIG =================
# API_URL reads from environment — set AXESSIA_API_URL in Azure App Service → Configuration
API_URL = os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan")
API_KEY = os.getenv("AXESSIA_API_KEY", "change-me-before-deploy")

SEVERITY_WEIGHTS = {
    "critical": 4,
    "serious": 3,
    "moderate": 2,
    "minor": 1,
}

CONFIDENCE_LABELS = {
    "automated": "🟢 Automated",
    "assisted":  "🟠 Assisted",
    "manual":    "🔴 Manual",
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
            timeout=90,
        )

        if response.status_code == 401:
            st.error("❌ Unauthorized. Check AXESSIA_API_KEY in App Settings.")
            return None
        if response.status_code == 429:
            st.warning("⏳ Rate limit exceeded. Please wait 60 seconds and try again.")
            return None
        if response.status_code >= 500:
            st.error("❌ Server error during scan. Check App Service logs.")
            return None

        return response.json()

    except requests.exceptions.Timeout:
        st.error("⏳ Scan timed out. The page may be too slow or complex.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to the scan API. Ensure the API worker is running.")
        return None
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
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

# ── Authenticated scan session state ──────────────────
if "auth_phase" not in st.session_state:
    st.session_state.auth_phase = "idle"
    # idle → logging_in → needs_manual_otp → authenticated → expired
if "auth_storage_state" not in st.session_state:
    st.session_state.auth_storage_state = None
if "auth_otp_url" not in st.session_state:
    st.session_state.auth_otp_url = None
if "auth_login_url" not in st.session_state:
    st.session_state.auth_login_url = ""
if "auth_otp_prefill" not in st.session_state:
    st.session_state.auth_otp_prefill = ""


st.title("⚡ Axessia – Accessibility Intelligence")

# ======================================================
# 🔐 AUTHENTICATED SCAN PANEL
# For URLs behind login (e.g. Sky test environment)
# ======================================================

with st.expander(
    "🔐 Authenticated Scan  —  for URLs behind login (Sky test environment, staging sites)",
    expanded=(st.session_state.auth_phase not in ("idle",)),
):
    phase = st.session_state.auth_phase

    # ── Status banner ──────────────────────────────
    if phase == "idle":
        st.info(
            "💡 Use this panel to scan pages that redirect to a login screen. "
            "Axessia will log in automatically and scan the real page content."
        )
    elif phase == "needs_manual_otp":
        st.warning(
            "⏳ One more step — the OTP code could not be read automatically. "
            "Check your SMS and enter the code below."
        )
    elif phase == "authenticated":
        st.success("✅ Session active — you can scan Sky test pages below.")
    elif phase == "expired":
        st.error("🔴 Session expired. Please log in again.")

    st.divider()

    # ════════════════════════════════════════════════
    # CREDENTIALS FORM
    # Shown when: idle, expired
    # ════════════════════════════════════════════════
    if phase in ("idle", "expired"):
        st.markdown("**Enter your Sky test account credentials**")
        st.caption(
            "Axessia will open the Sky login page, fill in your details, "
            "read the OTP code that appears on screen, and complete login "
            "— all automatically. You only need to provide email and password."
        )

        with st.container(border=True):
            auth_login_url = st.text_input(
                "Sky Login URL",
                value=st.session_state.auth_login_url
                      or "https://test-www.sky.it/login?clientID=WebSelfCare&forward=https%3A%2F%2Ftest.abbonamento.sky.it%2Fhome",
                key="auth_login_url_input",
            )
            auth_email    = st.text_input("Username or email", placeholder="your@email.com", key="auth_email_input")
            auth_password = st.text_input("Password", type="password", key="auth_password_input")

            if st.button("🚀 Log In Automatically", type="primary", key="auth_start_btn"):
                if not auth_email.strip() or not auth_password.strip():
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner(
                        "Logging in… Playwright is filling the form and reading the OTP code automatically…"
                    ):
                        result = fully_automated_login(
                            login_url = auth_login_url.strip(),
                            email     = auth_email.strip(),
                            password  = auth_password.strip(),
                        )

                    if result.get("success"):
                        st.session_state.auth_storage_state = result["storage_state"]
                        st.session_state.auth_login_url     = auth_login_url.strip()
                        st.session_state.auth_phase         = "authenticated"
                        otp = result.get("otp_used", "")
                        if otp:
                            st.toast(f"✅ Logged in! OTP used automatically: {otp}", icon="🔐")
                        st.rerun()

                    elif result.get("needs_manual_otp"):
                        # OTP not readable — fall back to manual entry
                        st.session_state.auth_storage_state = result["storage_state"]
                        st.session_state.auth_otp_url       = result["otp_url"]
                        st.session_state.auth_login_url     = auth_login_url.strip()
                        st.session_state.auth_otp_prefill   = result.get("otp_code_found", "")
                        st.session_state.auth_phase         = "needs_manual_otp"
                        st.rerun()

                    else:
                        st.error(f"Login failed: {result['error']}")

    # ════════════════════════════════════════════════
    # MANUAL OTP FALLBACK
    # Only shown when code was not readable from page
    # ════════════════════════════════════════════════
    elif phase == "needs_manual_otp":
        st.markdown("**Enter the SMS verification code**")
        with st.container(border=True):
            otp_val = st.text_input(
                "OTP / Security Code (6 digits)",
                value=st.session_state.auth_otp_prefill,
                max_chars=8,
                placeholder="e.g. 462628",
                key="auth_manual_otp_input",
            )
            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("✅ Submit Code", type="primary", key="auth_manual_otp_btn"):
                    if not otp_val.strip():
                        st.error("Please enter the verification code.")
                    else:
                        with st.spinner("Submitting code…"):
                            result = phase2_manual_otp(
                                otp_url       = st.session_state.auth_otp_url,
                                otp_code      = otp_val.strip(),
                                storage_state = st.session_state.auth_storage_state,
                            )
                        if result["success"]:
                            st.session_state.auth_storage_state = result["storage_state"]
                            st.session_state.auth_phase         = "authenticated"
                            st.rerun()
                        else:
                            st.error(f"Failed: {result['error']}")
                            st.info("💡 If the code expired, click Start Over and log in again.")
            with col2:
                if st.button("↩️ Start Over", key="auth_manual_restart_btn"):
                    st.session_state.auth_phase         = "idle"
                    st.session_state.auth_storage_state = None
                    st.session_state.auth_otp_url       = None
                    st.session_state.auth_otp_prefill   = ""
                    st.rerun()

    # ════════════════════════════════════════════════
    # AUTHENTICATED — Scan panel
    # ════════════════════════════════════════════════
    elif phase == "authenticated":
        st.markdown("**Scan a Sky test page**")
        st.caption(
            "Paste any URL from the Sky test environment. "
            "Your session cookies will be injected automatically."
        )
        with st.container(border=True):
            auth_scan_url = st.text_input(
                "URL to scan",
                placeholder="https://test.abbonamento.sky.it/offers",
                key="auth_scan_url_input",
            )

            col1, col2, col3 = st.columns([3, 2, 2])
            with col1:
                if st.button("🔍 Scan This Page", type="primary", key="auth_scan_btn"):
                    if not auth_scan_url.strip():
                        st.error("Please enter a URL to scan.")
                    else:
                        target = auth_scan_url.strip()
                        with st.spinner(f"Scanning {target} with your Sky session…"):
                            scan_result = run_scan_with_cookies(
                                url           = target,
                                storage_state = st.session_state.auth_storage_state,
                            )
                        if scan_result.get("session_expired"):
                            st.session_state.auth_phase = "expired"
                            st.rerun()
                        elif scan_result.get("error"):
                            st.error(f"Scan error: {scan_result['error']}")
                        else:
                            st.session_state.scan_results[target] = scan_result
                            st.session_state.view                 = "dashboard"
                            st.rerun()

            with col2:
                if st.button("🩺 Check Session", key="auth_check_btn"):
                    with st.spinner("Checking…"):
                        chk = verify_session(
                            target_url    = st.session_state.auth_login_url,
                            storage_state = st.session_state.auth_storage_state,
                        )
                    if chk["valid"]:
                        st.success(f"✅ Active")
                    else:
                        st.warning("⚠️ Expired")
                        st.session_state.auth_phase = "expired"
                        st.rerun()

            with col3:
                if st.button("🔄 Re-Login", key="auth_relogin_btn"):
                    st.session_state.auth_phase         = "idle"
                    st.session_state.auth_storage_state = None
                    st.rerun()

st.divider()

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
            url = st.text_input("Enter URL to scan", placeholder="https://example.com")
            if st.button("🔍 Run Scan", type="primary"):
                if url.strip():
                    with st.spinner("Running accessibility scan…"):
                        result = call_secure_scan(url.strip())
                        if result:
                            st.session_state.scan_results[url.strip()] = result
                            st.session_state.show_add_url = False
                            st.rerun()
                else:
                    st.warning("Please enter a valid URL")

    if not st.session_state.scan_results:
        st.info("🔎 No scans yet. Click **➕ Add URL** above to begin.")
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
                    title="Severity Distribution (All Scans)",
                    color_discrete_map={
                        "critical": "#C0392B",
                        "serious":  "#E67E22",
                        "moderate": "#F1C40F",
                        "minor":    "#27AE60",
                    },
                ),
                use_container_width=True,
            )

        with c2:
            scores = [
                {"URL": u[:50], "Score": calculate_score(pd.DataFrame(d.get("rules", [])))}
                for u, d in st.session_state.scan_results.items()
            ]
            st.plotly_chart(
                px.bar(
                    pd.DataFrame(scores),
                    x="URL",
                    y="Score",
                    title="Accessibility Score per URL",
                    color="Score",
                    color_continuous_scale="RdYlGn",
                    range_color=[0, 100],
                ),
                use_container_width=True,
            )

    st.divider()

    for url, result in st.session_state.scan_results.items():
        with st.container(border=True):
            st.markdown(f"### {url}")

            if "rules" not in result:
                st.error("Scan failed or returned no data.")
                continue

            df = pd.DataFrame(result["rules"])
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("♿ Score", f"{calculate_score(df)}%")
            c2.metric("🔴 Failures", len(df[df["status"] == "fail"]))
            c3.metric("🟢 Passed", len(df[df["status"] == "pass"]))
            c4.metric("🟠 Needs Review", len(df[df["status"].isin(["manual", "assisted"])]))

            a1, a2, a3 = st.columns(3)
            if a1.button("📊 View Results", key=f"view_{url}"):
                st.session_state.active_url = url
                st.session_state.view = "results"
                st.rerun()

            a2.download_button(
                "📄 Export PDF",
                data=generate_pdf_report(url, result),
                file_name=f"axessia_{url.replace('https://','').replace('http://','').replace('/','_')[:50]}.pdf",
                mime="application/pdf",
                key=f"pdf_{url}",
            )

            if a3.button("🗑️ Remove", key=f"del_{url}"):
                del st.session_state.scan_results[url]
                st.rerun()


# ======================================================
# RESULTS VIEW
# ======================================================
if st.session_state.view == "results":

    url  = st.session_state.active_url
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
        "📊 Overview",
        "📋 WCAG",
        "🔴 Issues",
        "🟠 Manual & Assisted",
        "🛠️ AI Agent – Dev",
        "🧪 AI Agent – QA",
        "⚖️ EAA Readiness",
    ])

    # ── OVERVIEW ──────────────────────────────────────
    with tabs[0]:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🔴 Failures",     len(df[df["status"] == "fail"]))
        c2.metric("🟢 Passed",       len(df[df["status"] == "pass"]))
        c3.metric("🟠 Needs Review", len(df[df["status"].isin(["manual","assisted"])]))
        c4.metric("📋 Total Rules",  len(df))

        st.metric("♿ Severity-Weighted Score", f"{calculate_score(df)}%")

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                px.pie(
                    df.groupby("severity").size().reset_index(name="count"),
                    names="severity", values="count", hole=0.5,
                    title="Issues by Severity",
                    color_discrete_map={
                        "critical": "#C0392B", "serious": "#E67E22",
                        "moderate": "#F1C40F", "minor":   "#27AE60",
                    },
                ),
                use_container_width=True,
            )
        with col2:
            st.plotly_chart(
                px.density_heatmap(
                    df, x="wcag", y="severity",
                    title="Severity × WCAG Heatmap",
                ),
                use_container_width=True,
            )

    # ── WCAG TABLE ────────────────────────────────────
    with tabs[1]:
        t = df.copy()
        t["Confidence"] = t["test_type"].map(CONFIDENCE_LABELS)
        st.dataframe(
            t[["name","wcag","level","severity","status","Confidence"]],
            use_container_width=True,
            hide_index=True,
        )

    # ── ISSUES ────────────────────────────────────────
    with tabs[2]:
        failed = df[df["status"] == "fail"]
        if failed.empty:
            st.success("🎉 No failures detected!")
        for i, r in failed.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"🔴 {r['name']}  |  WCAG {r['wcag']}  |  {r['severity'].upper()}"):
                if ai.get("why_not_automated"):
                    st.markdown("**Why this fails**")
                    st.write(ai["why_not_automated"])
                if ai.get("who_is_impacted"):
                    st.markdown("**Who is impacted**")
                    st.write(ai["who_is_impacted"])
                if ai.get("legal_risk"):
                    st.markdown("**Legal / Compliance Risk**")
                    st.write(ai["legal_risk"])
                if ai.get("what_to_test_manually"):
                    st.markdown("**How to Fix**")
                    st.write(ai["what_to_test_manually"])
                if r.get("instances"):
                    st.markdown("**Affected HTML**")
                    for inst in r["instances"][:3]:
                        if inst.get("snippet"):
                            st.code(inst["snippet"], language="html")

    # ── MANUAL & ASSISTED ─────────────────────────────
    with tabs[3]:
        review = df[df["status"].isin(["manual","assisted"])]
        if review.empty:
            st.success("No manual checks required.")
        for _, r in review.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            label = CONFIDENCE_LABELS.get(r["test_type"], r["test_type"])
            with st.expander(f"{label}  {r['name']}  |  WCAG {r['wcag']}"):
                if ai.get("why_not_automated"):
                    st.markdown("**Why manual testing is required**")
                    st.write(ai["why_not_automated"])
                if ai.get("what_to_test_manually"):
                    st.markdown("**What to verify**")
                    st.write(ai["what_to_test_manually"])
                if ai.get("qa_validation_steps"):
                    st.markdown("**QA Validation Steps**")
                    for step in ai["qa_validation_steps"]:
                        st.write(f"— {step}")

    # ── AI AGENT – DEV ────────────────────────────────
    with tabs[4]:
        failed_dev = df[df["status"] == "fail"]
        if failed_dev.empty:
            st.success("No failures to fix.")
        for _, r in failed_dev.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"🛠️ Fix: {r['name']}  (WCAG {r['wcag']})"):
                if r.get("instances"):
                    st.markdown("**Affected HTML snippet**")
                    st.code(r["instances"][0].get("snippet", ""), language="html")
                if ai.get("what_to_test_manually"):
                    st.markdown("**Developer Action**")
                    st.write(ai["what_to_test_manually"])

    # ── AI AGENT – QA ─────────────────────────────────
    with tabs[5]:
        rows = []
        for _, r in df[df["status"].isin(["manual","assisted"])].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            rows.append({
                "Rule":       r["name"],
                "WCAG":       r["wcag"],
                "Severity":   r["severity"],
                "Confidence": CONFIDENCE_LABELS.get(r["test_type"], r["test_type"]),
                "Test Steps": " → ".join(ai.get("qa_validation_steps", [])),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No manual or assisted rules to review.")

    # ── EAA READINESS ─────────────────────────────────
    with tabs[6]:
        high = df[
            (df["level"].isin(["A","AA"])) &
            (df["severity"].isin(["critical","serious"])) &
            (df["status"] != "pass")
        ]

        if not high.empty:
            st.error("🔴 HIGH EAA Risk — Critical WCAG A/AA failures present")
        else:
            st.success("🟢 LOW EAA Risk — No critical blockers detected")

        for _, r in high.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            if ai.get("legal_risk"):
                with st.expander(f"{r['name']}  |  WCAG {r['wcag']}"):
                    st.write(ai["legal_risk"])
