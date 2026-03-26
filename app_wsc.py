import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from pdf_report import generate_pdf_report
from auth_flow import parse_cookies, verify_session_from_cookies, verify_session
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

    if phase == "idle":
        st.info(
            "💡 Sky's firewall blocks automated login from cloud servers. "
            "Log in manually in your browser, export your cookies, and paste them here. "
            "Axessia will use those cookies to scan any Sky test page."
        )
    elif phase == "authenticated":
        st.success("✅ Cookies imported — session active. Scan Sky test pages below.")
    elif phase == "expired":
        st.error("🔴 Session expired. Please import fresh cookies.")

    st.divider()

    if phase in ("idle", "expired"):
        st.markdown("**Step 1** — Install [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkaldje) extension in Chrome (free, one-time)")
        st.markdown("**Step 2** — Log into `test-www.sky.it` normally in your browser")
        st.markdown("**Step 3** — Click the Cookie-Editor icon → **Export** → **Export as JSON** → copies to clipboard")
        st.markdown("**Step 4** — Paste below and click Import")

        cookie_input = st.text_area(
            "Paste cookies here (JSON from Cookie-Editor)",
            height=150,
            placeholder='[{"name":"session","value":"abc123","domain":".sky.it",...}, ...]',
            key="cookie_paste_input",
        )

        if st.button("✅ Import Cookies & Activate Session", type="primary", key="cookie_import_btn"):
            if not cookie_input.strip():
                st.error("Please paste your cookies first.")
            else:
                storage_state = parse_cookies(cookie_input.strip())
                if not storage_state:
                    st.error(
                        "Could not parse the cookies. "
                        "Make sure you used **Export as JSON** in Cookie-Editor."
                    )
                else:
                    with st.spinner("Verifying session with Sky test environment…"):
                        check = verify_session_from_cookies(
                            target_url    = "https://test.abbonamento.sky.it/home",
                            storage_state = storage_state,
                        )
                    num_cookies = len(storage_state.get("cookies", []))
                    st.session_state.auth_storage_state = storage_state
                    st.session_state.auth_login_url     = "https://test.abbonamento.sky.it/home"
                    st.session_state.auth_phase         = "authenticated"
                    if not check["valid"]:
                        st.warning(
                            f"Imported {num_cookies} cookies but session check landed on "
                            f"`{check.get('landed_url','?')}` — cookies may be expired."
                        )
                    st.rerun()

    elif phase == "authenticated":
        num = len(st.session_state.auth_storage_state.get("cookies", []))
        st.caption(f"🍪 {num} cookies active")

        auth_scan_url = st.text_input(
            "URL to scan",
            placeholder="https://test.abbonamento.sky.it/offers",
            key="auth_scan_url_input",
        )

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

        if st.button("🩺 Check if session is still active", key="auth_check_btn"):
            with st.spinner("Checking…"):
                chk = verify_session_from_cookies(
                    target_url    = st.session_state.auth_login_url or "https://test.abbonamento.sky.it/home",
                    storage_state = st.session_state.auth_storage_state,
                )
            if chk["valid"]:
                st.success(f"✅ Session active — {chk.get('page_title', chk['landed_url'])}")
            else:
                st.warning(f"⚠️ Expired — redirected to: {chk['landed_url']}")
                st.session_state.auth_phase = "expired"
                st.rerun()

        if st.button("🔄 Import New Cookies", key="auth_relogin_btn"):
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

    # ── Extension scan results ─────────────────────────
    API_BASE = os.getenv("AXESSIA_API_URL", "http://127.0.0.1:8001/scan").replace("/scan", "")

    st.divider()
    ext_col1, ext_col2 = st.columns([6, 1])
    ext_col1.subheader("🔌 Extension Scans")
    if ext_col2.button("🔄 Refresh", key="ext_refresh"):
        st.rerun()

    try:
        ext_resp = requests.get(
            f"{API_BASE}/ingested",
            headers={"x-api-key": API_KEY},
            timeout=5,
        )
        ext_results = ext_resp.json() if ext_resp.status_code == 200 else {}
    except Exception:
        ext_results = {}

    if ext_results:
        for ext_url, ext_data in ext_results.items():
            with st.container(border=True):
                st.markdown(f"**{ext_url}**")
                session  = ext_data.get("session_name", "Extension Scan")
                scanned  = ext_data.get("scanned_at", "")
                st.caption(f"📋 {session}  ·  🕐 {scanned[:16] if scanned else 'Unknown time'}")
                if "rules" in ext_data:
                    df_ext = pd.DataFrame(ext_data["rules"])
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("♿ Score",        f"{calculate_score(df_ext)}%")
                    c2.metric("🔴 Failures",     len(df_ext[df_ext["status"] == "fail"]))
                    c3.metric("🟢 Passed",       len(df_ext[df_ext["status"] == "pass"]))
                    c4.metric("🟠 Needs Review", len(df_ext[df_ext["status"].isin(["manual","assisted"])]))

                    b1, b2, b3 = st.columns(3)
                    if b1.button("📊 View Results", key=f"ext_view_{ext_url}"):
                        st.session_state.scan_results[ext_url] = ext_data
                        st.session_state.active_url = ext_url
                        st.session_state.view = "results"
                        st.rerun()
                    b2.download_button(
                        "📄 Export PDF",
                        data=generate_pdf_report(ext_url, ext_data),
                        file_name=f"axessia_ext_{ext_url.replace('https://','').replace('/','_')[:40]}.pdf",
                        mime="application/pdf",
                        key=f"ext_pdf_{ext_url}",
                    )
                    if b3.button("🗑️ Remove", key=f"ext_del_{ext_url}"):
                        try:
                            requests.delete(
                                f"{API_BASE}/ingested",
                                headers={"x-api-key": API_KEY},
                                timeout=5,
                            )
                        except Exception:
                            pass
                        st.rerun()
    else:
        st.info(
            "No extension scans yet. Install the Axessia Chrome extension, "
            "navigate to any page (including Sky test environment), and click Scan."
        )

    if not st.session_state.scan_results:
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