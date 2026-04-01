import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os
from pdf_report import generate_pdf_report
from auth_flow import parse_cookies, verify_session_from_cookies
from scanner_axe import run_scan_with_cookies

# ── Config ────────────────────────────────────────────
API_URL   = os.getenv("AXESSIA_API_URL",  "http://127.0.0.1:8001/scan")
CRAWL_URL = os.getenv("AXESSIA_API_URL",  "http://127.0.0.1:8001/scan").replace("/scan", "/crawl")
API_KEY   = os.getenv("AXESSIA_API_KEY",  "super-secret-demo-key")

SEVERITY_WEIGHTS = {"critical": 4, "serious": 3, "moderate": 2, "minor": 1}
CONFIDENCE_LABELS = {
    "automated": "🟢 Automated",
    "assisted":  "🟠 Assisted",
    "manual":    "🔴 Manual",
}

# ── Helpers ───────────────────────────────────────────
def safe_ai(val):
    return val if isinstance(val, dict) else {}

def calculate_score(df: pd.DataFrame) -> float:
    if df.empty: return 0.0
    df = df.copy()
    df["weight"] = df["severity"].map(SEVERITY_WEIGHTS).fillna(0)
    max_score    = len(df) * max(SEVERITY_WEIGHTS.values())
    passed_score = df[df["status"] == "pass"]["weight"].sum()
    return round((passed_score / max_score) * 100, 1) if max_score else 0.0

def call_secure_scan(url: str):
    try:
        r = requests.post(
            API_URL,
            headers={"Content-Type": "application/json", "x-api-key": API_KEY},
            json={"url": url},
            timeout=90,
        )
        if r.status_code == 401:   st.error("Unauthorized. Check AXESSIA_API_KEY."); return None
        if r.status_code == 429:   st.warning("Rate limit exceeded. Wait and retry."); return None
        if r.status_code >= 500:   st.error("Server error during scan."); return None
        return r.json()
    except requests.exceptions.Timeout:         st.error("Scan timed out."); return None
    except requests.exceptions.ConnectionError: st.error("Cannot connect to API."); return None
    except Exception as e:                      st.error(f"Error: {e}"); return None

# ── Session state ─────────────────────────────────────
for k, v in {
    "view": "dashboard", "active_url": None, "scan_results": {},
    "show_add_url": False, "crawl_results": None,
    "auth_phase": "idle", "auth_storage_state": None,
    "auth_login_url": "https://test.abbonamento.sky.it/home",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ======================================================
# 🔐 COOKIE IMPORT PANEL (for Sky test environment)
# ======================================================
with st.expander(
    "🔐 Authenticated Scan — for pages behind login (Sky test environment)",
    expanded=(st.session_state.auth_phase != "idle"),
):
    phase = st.session_state.auth_phase

    if phase == "idle":
        st.info(
            "💡 Log into the Sky test environment in your browser, export cookies "
            "using **Cookie-Editor** or **Cookie Manager** extension, paste below."
        )
    elif phase == "authenticated":
        num = len(st.session_state.auth_storage_state.get("cookies", []))
        st.success(f"✅ {num} cookies active — scan any Sky test page below.")
    elif phase == "expired":
        st.error("🔴 Session expired. Please import fresh cookies.")

    st.divider()

    if phase in ("idle", "expired"):
        st.markdown(
            "**How to get cookies (30 seconds):**\n\n"
            "1. Install [Cookie-Editor](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkaldje) "
            "or [Cookie Manager](https://chrome.google.com/webstore/detail/cookie-manager/gnlibmlfpencglodjpgnalbdebfhpmfg) in Chrome\n"
            "2. Log into `test-www.sky.it` normally\n"
            "3. Click the extension → **Export** → **Export as JSON** → copies to clipboard\n"
            "4. Paste below and click Import"
        )
        cookie_input = st.text_area(
            "Paste cookies here (JSON from Cookie-Editor or Cookie Manager)",
            height=120,
            placeholder='[{"name":"session","value":"abc123","domain":".sky.it",...}]',
            key="cookie_paste_input",
        )
        if st.button("✅ Import Cookies", type="primary", key="cookie_import_btn"):
            if not cookie_input.strip():
                st.error("Please paste your cookies first.")
            else:
                storage_state = parse_cookies(cookie_input.strip())
                if not storage_state:
                    st.error("Could not parse cookies. Use **Export as JSON** in Cookie-Editor.")
                else:
                    with st.spinner("Verifying session…"):
                        check = verify_session_from_cookies(
                            "https://test.abbonamento.sky.it/home", storage_state
                        )
                    num = len(storage_state.get("cookies", []))
                    st.session_state.auth_storage_state = storage_state
                    st.session_state.auth_login_url     = "https://test.abbonamento.sky.it/home"
                    st.session_state.auth_phase         = "authenticated"
                    if not check["valid"]:
                        st.warning(
                            f"Imported {num} cookies but session check landed on "
                            f"`{check.get('landed_url','?')}` — cookies may be expired."
                        )
                    st.rerun()

    elif phase == "authenticated":
        auth_scan_url = st.text_input(
            "URL to scan (Sky test environment)",
            placeholder="https://test.abbonamento.sky.it/offers",
            key="auth_scan_url_input",
        )
        if st.button("🔍 Scan This Page", type="primary", key="auth_scan_btn"):
            if not auth_scan_url.strip():
                st.error("Please enter a URL.")
            else:
                with st.spinner(f"Scanning {auth_scan_url.strip()} with your Sky session…"):
                    result = run_scan_with_cookies(
                        url=auth_scan_url.strip(),
                        storage_state=st.session_state.auth_storage_state,
                    )
                if result.get("session_expired"):
                    st.session_state.auth_phase = "expired"
                    st.rerun()
                elif result.get("error"):
                    st.error(f"Scan error: {result['error']}")
                else:
                    st.session_state.scan_results[auth_scan_url.strip()] = result
                    st.session_state.view = "dashboard"
                    st.rerun()

        if st.button("🩺 Check Session", key="auth_check_btn"):
            with st.spinner("Checking…"):
                chk = verify_session_from_cookies(
                    st.session_state.auth_login_url,
                    st.session_state.auth_storage_state,
                )
            if chk["valid"]:
                st.success(f"✅ Active — {chk.get('page_title', chk['landed_url'])}")
            else:
                st.warning("⚠️ Session expired.")
                st.session_state.auth_phase = "expired"
                st.rerun()

        if st.button("🔄 Import New Cookies", key="auth_new_btn"):
            st.session_state.auth_phase         = "idle"
            st.session_state.auth_storage_state = None
            st.rerun()

st.divider()

# ======================================================
# DASHBOARD VIEW
# ======================================================
if st.session_state.view == "dashboard":

    # ── Scan mode selector ─────────────────────────────
    scan_mode = st.radio(
        "mode", ["🔍 Single URL Scan", "🕷️ Site Crawl"],
        horizontal=True, label_visibility="collapsed", key="scan_mode",
    )
    st.divider()

    # ══════════════════════════════════════════════════
    # SINGLE URL MODE
    # ══════════════════════════════════════════════════
    if scan_mode == "🔍 Single URL Scan":

        h1, h2 = st.columns([6, 1])
        h1.subheader("Scan Results")
        if h2.button("➕ Add URL"):
            st.session_state.show_add_url = not st.session_state.show_add_url

        if st.session_state.show_add_url:
            with st.container(border=True):
                url = st.text_input("Enter URL to scan", placeholder="https://example.com")
                if st.button("🔍 Run Scan", type="primary"):
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
            st.info("🔎 No scans yet. Click **➕ Add URL** to begin.")
        else:
            # Charts
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
                            names="severity", values="count", hole=0.4,
                            title="Severity Distribution",
                            color_discrete_map={"critical":"#C0392B","serious":"#E67E22","moderate":"#F1C40F","minor":"#27AE60"},
                        ), use_container_width=True,
                    )
                with c2:
                    scores = [{"URL": u[:50], "Score": calculate_score(pd.DataFrame(d.get("rules", [])))}
                              for u, d in st.session_state.scan_results.items()]
                    st.plotly_chart(
                        px.bar(pd.DataFrame(scores), x="URL", y="Score", title="Score per URL",
                               color="Score", color_continuous_scale="RdYlGn", range_color=[0,100]),
                        use_container_width=True,
                    )

            st.divider()

            for url, result in st.session_state.scan_results.items():
                with st.container(border=True):
                    st.markdown(f"### {url}")
                    if "rules" not in result:
                        st.error("Scan failed."); continue

                    df = pd.DataFrame(result["rules"])
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("♿ Score",        f"{calculate_score(df)}%")
                    c2.metric("🔴 Failures",     len(df[df["status"] == "fail"]))
                    c3.metric("🟢 Passed",       len(df[df["status"] == "pass"]))
                    c4.metric("🟠 Needs Review", len(df[df["status"].isin(["manual","assisted"])]))

                    a1, a2, a3 = st.columns(3)
                    if a1.button("📊 View Results", key=f"view_{url}"):
                        st.session_state.active_url = url
                        st.session_state.view = "results"
                        st.rerun()
                    a2.download_button(
                        "📄 Export PDF",
                        data=generate_pdf_report(url, result),
                        file_name=f"axessia_{url.replace('https://','').replace('/','_')[:50]}.pdf",
                        mime="application/pdf", key=f"pdf_{url}",
                    )
                    if a3.button("🗑️ Remove", key=f"del_{url}"):
                        del st.session_state.scan_results[url]
                        st.rerun()

    # ══════════════════════════════════════════════════
    # SITE CRAWL MODE
    # ══════════════════════════════════════════════════
    else:

        st.subheader("🕷️ Site Crawl")
        st.caption("Enter a seed URL — Axessia discovers all sections and scans multiple pages automatically.")

        with st.container(border=True):
            crawl_seed = st.text_input(
                "Seed URL", placeholder="https://example.com", key="crawl_seed",
            )
            max_pages = st.slider(
                "Max pages per section", min_value=1, max_value=5, value=2, key="crawl_max_pages",
            )
            if st.button("🕷️ Start Crawl", type="primary", key="crawl_btn"):
                if not crawl_seed.strip():
                    st.error("Please enter a seed URL.")
                else:
                    with st.spinner("Crawling site… discovering sections and scanning pages. This may take up to 2 minutes."):
                        try:
                            resp = requests.post(
                                CRAWL_URL,
                                headers={"Content-Type": "application/json", "x-api-key": API_KEY},
                                json={"seed_url": crawl_seed.strip(), "max_pages_per_section": max_pages},
                                timeout=180,
                            )
                            if resp.status_code == 200:
                                st.session_state.crawl_results = resp.json()
                                st.rerun()
                            else:
                                st.error(f"Crawl failed: HTTP {resp.status_code}")
                        except requests.exceptions.Timeout:
                            st.error("Crawl timed out. Try reducing max pages per section to 1.")
                        except Exception as e:
                            st.error(f"Crawl error: {str(e)}")

        # ── Crawl results ──────────────────────────────
        if st.session_state.crawl_results:
            crawl_data = st.session_state.crawl_results
            sections   = crawl_data.get("sections", {})

            if sections:
                total_pages    = sum(len(s.get("pages", [])) for s in sections.values())
                total_failures = sum(
                    sum(1 for r in (s.get("rules") or []) if r.get("status") == "fail")
                    for s in sections.values()
                )
                avg_score = round(
                    sum(s.get("section_score", 0) for s in sections.values()) / len(sections), 1
                ) if sections else 0

                st.divider()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("📂 Sections",       len(sections))
                c2.metric("📄 Pages Scanned",  total_pages)
                c3.metric("🔴 Total Failures", total_failures)
                c4.metric("♿ Avg Score",       f"{avg_score}%")
                st.divider()

                for section_name, section_data in sections.items():
                    risk     = section_data.get("eaa_risk", "Low")
                    score    = section_data.get("section_score", 0)
                    pages    = section_data.get("pages", [])
                    rules    = section_data.get("rules") or []
                    failures = [r for r in rules if r.get("status") == "fail"]

                    risk_icon = {"High": "🔴", "Medium": "🟠", "Low": "🟢"}.get(risk, "🟡")

                    with st.container(border=True):
                        col1, col2, col3 = st.columns([4, 2, 2])
                        col1.markdown(f"### 📁 {section_name}")
                        col1.caption(f"{len(pages)} page(s) scanned")
                        col2.metric("Score",    f"{score}%")
                        col3.metric("EAA Risk", f"{risk_icon} {risk}")

                        if failures:
                            with st.expander(f"🔴 {len(failures)} failure(s) in this section"):
                                for r in failures[:15]:
                                    st.markdown(f"- **{r.get('name')}** — WCAG {r.get('wcag')} · {r.get('severity')}")

                        for pg in pages:
                            st.caption(f"  • {pg}")

                st.divider()
                if st.button("🗑️ Clear Crawl Results", key="clear_crawl"):
                    st.session_state.crawl_results = None
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
        st.session_state.view      = "dashboard"
        st.session_state.active_url = None
        st.rerun()

    st.markdown(f"## Results for `{url}`")

    tabs = st.tabs([
        "📊 Overview", "📋 WCAG", "🔴 Issues",
        "🟠 Manual & Assisted", "🛠️ AI Agent – Dev",
        "🧪 AI Agent – QA", "⚖️ EAA Readiness",
    ])

    # ── Overview ──────────────────────────────────────
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
                px.pie(df.groupby("severity").size().reset_index(name="count"),
                       names="severity", values="count", hole=0.5, title="Issues by Severity"),
                use_container_width=True,
            )
        with col2:
            st.plotly_chart(
                px.density_heatmap(df, x="wcag", y="severity", title="Severity × WCAG"),
                use_container_width=True,
            )

    # ── WCAG table ────────────────────────────────────
    with tabs[1]:
        t = df.copy()
        t["Confidence"] = t["test_type"].map(CONFIDENCE_LABELS)
        st.dataframe(
            t[["name","wcag","level","severity","status","Confidence"]],
            use_container_width=True, hide_index=True,
        )

    # ── Issues ────────────────────────────────────────
    with tabs[2]:
        failed = df[df["status"] == "fail"]
        if failed.empty:
            st.success("🎉 No failures detected!")
        for i, r in failed.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"🔴 {r['name']}  |  WCAG {r['wcag']}  |  {r['severity'].upper()}"):
                if ai.get("why_not_automated"):
                    st.markdown("**Why this fails**"); st.write(ai["why_not_automated"])
                if ai.get("who_is_impacted"):
                    st.markdown("**Who is impacted**"); st.write(ai["who_is_impacted"])
                if ai.get("legal_risk"):
                    st.markdown("**Legal / Compliance Risk**"); st.write(ai["legal_risk"])
                if ai.get("what_to_test_manually"):
                    st.markdown("**How to Fix**"); st.write(ai["what_to_test_manually"])
                if r.get("instances"):
                    st.markdown("**Affected HTML**")
                    for inst in r["instances"][:3]:
                        if inst.get("snippet"):
                            st.code(inst["snippet"], language="html")
                st.markdown(
                    '<button style="background:transparent;border:1.5px solid #C8196E;'
                    'color:#C8196E;padding:6px 16px;border-radius:8px;font-size:0.85rem;'
                    'font-weight:600;cursor:pointer;margin-top:8px;">'
                    '🧾 Create Defect</button>',
                    unsafe_allow_html=True,
                )

    # ── Manual & Assisted ─────────────────────────────
    with tabs[3]:
        review = df[df["status"].isin(["manual","assisted"])]
        if review.empty:
            st.success("No manual checks required.")
        for _, r in review.iterrows():
            ai    = safe_ai(r.get("ai_explanation"))
            label = CONFIDENCE_LABELS.get(r["test_type"], r["test_type"])
            with st.expander(f"{label}  {r['name']}  |  WCAG {r['wcag']}"):
                if ai.get("why_not_automated"):
                    st.markdown("**Why manual testing is required**"); st.write(ai["why_not_automated"])
                if ai.get("what_to_test_manually"):
                    st.markdown("**What to verify**"); st.write(ai["what_to_test_manually"])
                if ai.get("qa_validation_steps"):
                    st.markdown("**QA Validation Steps**")
                    for step in ai["qa_validation_steps"]:
                        st.write(f"— {step}")

    # ── AI Agent – Dev ────────────────────────────────
    with tabs[4]:
        failed_dev = df[df["status"] == "fail"]
        if failed_dev.empty:
            st.success("No failures to fix.")
        for _, r in failed_dev.iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            with st.expander(f"🛠️ Fix: {r['name']}  (WCAG {r['wcag']})"):
                if r.get("instances"):
                    st.markdown("**Affected HTML**")
                    st.code(r["instances"][0].get("snippet", ""), language="html")
                if ai.get("what_to_test_manually"):
                    st.markdown("**Developer Action**"); st.write(ai["what_to_test_manually"])

    # ── AI Agent – QA ─────────────────────────────────
    with tabs[5]:
        rows = []
        for _, r in df[df["status"].isin(["manual","assisted"])].iterrows():
            ai = safe_ai(r.get("ai_explanation"))
            rows.append({
                "Rule": r["name"], "WCAG": r["wcag"], "Severity": r["severity"],
                "Confidence": CONFIDENCE_LABELS.get(r["test_type"], r["test_type"]),
                "Test Steps": " → ".join(ai.get("qa_validation_steps", [])),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No manual or assisted rules to review.")

    # ── EAA Readiness ─────────────────────────────────
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