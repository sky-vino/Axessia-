import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import base64
import os
import json
import sqlite3
from datetime import datetime

from pdf_report import generate_pdf_report
from auth_flow import parse_cookies, verify_session_from_cookies
from scanner_axe import run_scan_with_cookies

# ── Config ────────────────────────────────────────────
API_URL   = os.getenv("AXESSIA_API_URL",  "http://127.0.0.1:8001/scan")
CRAWL_URL = API_URL.replace("/scan", "/crawl")
API_KEY   = os.getenv("AXESSIA_API_KEY",  "super-secret-demo-key")

SEVERITY_WEIGHTS = {"critical":4,"serious":3,"moderate":2,"minor":1}
CONFIDENCE_LABELS = {
    "automated": "🟢 Automated",
    "assisted":  "🟠 Assisted",
    "manual":    "🔴 Manual",
}
SEV_COLORS = {"critical":"#E24B4A","serious":"#EF9F27","moderate":"#378ADD","minor":"#639922"}

# ── Trend DB ──────────────────────────────────────────
def _trend_db():
    conn = sqlite3.connect("scan_history.db", check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            url      TEXT,
            score    REAL,
            failures INTEGER,
            eaa_risk TEXT,
            scanned  TEXT
        )
    """)
    conn.commit()
    return conn

def save_to_history(url, result):
    try:
        from scoring import calculate_score
        from eaa_mapping import evaluate_eaa
        rules  = result.get("rules", [])
        score  = calculate_score(rules).get("score", 0)
        eaa    = evaluate_eaa(rules)
        fails  = len([r for r in rules if r.get("status") == "fail"])
        conn   = _trend_db()
        conn.execute(
            "INSERT INTO history (url,score,failures,eaa_risk,scanned) VALUES (?,?,?,?,?)",
            (url, score, fails, eaa.get("risk_level","—"), datetime.now().isoformat())
        )
        conn.commit(); conn.close()
    except Exception: pass

def get_history(url):
    try:
        conn  = _trend_db()
        rows  = conn.execute(
            "SELECT score,failures,eaa_risk,scanned FROM history WHERE url=? ORDER BY scanned DESC LIMIT 20",
            (url,)
        ).fetchall()
        conn.close()
        return [{"score":r[0],"failures":r[1],"eaa_risk":r[2],"scanned":r[3]} for r in rows]
    except Exception: return []

# ── Helpers ───────────────────────────────────────────
def safe_ai(val): return val if isinstance(val, dict) else {}

def calculate_score(df):
    if df.empty: return 0.0
    df = df.copy()
    df["weight"] = df["severity"].map(SEVERITY_WEIGHTS).fillna(0)
    max_s = len(df) * max(SEVERITY_WEIGHTS.values())
    passed = df[df["status"]=="pass"]["weight"].sum()
    return round((passed/max_s)*100,1) if max_s else 0.0

def call_secure_scan(url):
    try:
        r = requests.post(
            API_URL,
            headers={"Content-Type":"application/json","x-api-key":API_KEY},
            json={"url":url},
            timeout=120,
        )
        if r.status_code == 401: st.error("Unauthorized — check API key."); return None
        if r.status_code == 429: st.warning("Rate limit — wait and retry."); return None
        if r.status_code >= 500: st.error("Server error during scan."); return None
        return r.json()
    except requests.exceptions.Timeout: st.error("Scan timed out."); return None
    except Exception as e: st.error(f"Error: {e}"); return None

def show_screenshot(b64, caption=""):
    if b64:
        img_bytes = base64.b64decode(b64)
        st.image(img_bytes, caption=caption, use_column_width=True)

# ── Session state ─────────────────────────────────────
for k,v in {
    "view":"dashboard","active_url":None,"scan_results":{},
    "show_add_url":False,"crawl_results":None,
    "auth_phase":"idle","auth_storage_state":None,
    "auth_login_url":"https://test.abbonamento.sky.it/home",
}.items():
    if k not in st.session_state: st.session_state[k]=v

# ══════════════════════════════════════════════════════
# COOKIE IMPORT PANEL
# ══════════════════════════════════════════════════════
with st.expander(
    "🔐 Authenticated Scan — Sky test environment (behind login)",
    expanded=(st.session_state.auth_phase != "idle"),
):
    phase = st.session_state.auth_phase

    if phase == "idle":
        st.info("Log into Sky test environment in Chrome → export cookies using Cookie-Editor → paste below.")
    elif phase == "authenticated":
        num = len(st.session_state.auth_storage_state.get("cookies",[]))
        st.success(f"✅ {num} cookies active — scan any Sky test page below.")
    elif phase == "expired":
        st.error("🔴 Session expired — import fresh cookies.")

    st.divider()

    if phase in ("idle","expired"):
        cookie_input = st.text_area(
            "Paste cookies JSON (from Cookie-Editor → Export as JSON)",
            height=100, placeholder='[{"name":"session","value":"...","domain":".sky.it",...}]',
            key="cookie_paste",
        )
        if st.button("✅ Import Cookies", type="primary", key="import_btn"):
            if not cookie_input.strip():
                st.error("Paste your cookies first.")
            else:
                storage = parse_cookies(cookie_input.strip())
                if not storage:
                    st.error("Could not parse cookies. Use Export as JSON in Cookie-Editor.")
                else:
                    with st.spinner("Verifying session…"):
                        check = verify_session_from_cookies("https://test.abbonamento.sky.it/home", storage)
                    st.session_state.auth_storage_state = storage
                    st.session_state.auth_phase = "authenticated"
                    if not check.get("valid"):
                        st.warning(f"Cookies imported but session landed on {check.get('landed_url','?')} — may be expired.")
                    st.rerun()

    elif phase == "authenticated":
        auth_url = st.text_input("URL to scan (Sky test page)", placeholder="https://test.abbonamento.sky.it/offers", key="auth_url")
        c1, c2, c3 = st.columns(3)
        if c1.button("🔍 Scan This Page", type="primary", key="auth_scan"):
            if not auth_url.strip():
                st.error("Enter a URL.")
            else:
                with st.spinner(f"Scanning {auth_url.strip()} with your session…"):
                    result = run_scan_with_cookies(auth_url.strip(), st.session_state.auth_storage_state)
                if result.get("session_expired"):
                    st.session_state.auth_phase = "expired"; st.rerun()
                elif result.get("error"):
                    st.error(f"Scan error: {result['error']}")
                else:
                    save_to_history(auth_url.strip(), result)
                    st.session_state.scan_results[auth_url.strip()] = result
                    st.session_state.view = "dashboard"; st.rerun()
        if c2.button("🩺 Check Session", key="auth_check"):
            with st.spinner("Checking…"):
                chk = verify_session_from_cookies(st.session_state.auth_login_url, st.session_state.auth_storage_state)
            if chk.get("valid"): st.success("✅ Active")
            else:
                st.warning("⚠️ Expired"); st.session_state.auth_phase = "expired"; st.rerun()
        if c3.button("🔄 New Cookies", key="auth_new"):
            st.session_state.auth_phase = "idle"; st.session_state.auth_storage_state = None; st.rerun()

st.divider()

# ══════════════════════════════════════════════════════
# DASHBOARD VIEW
# ══════════════════════════════════════════════════════
if st.session_state.view == "dashboard":

    scan_mode = st.radio("mode", ["🔍 Single URL Scan","🕷️ Site Crawl"],
                         horizontal=True, label_visibility="collapsed", key="scan_mode")
    st.divider()

    # ── SINGLE URL ────────────────────────────────────
    if scan_mode == "🔍 Single URL Scan":

        h1, h2 = st.columns([6,1])
        h1.subheader("Scan Results")
        if h2.button("➕ Add URL"): st.session_state.show_add_url = not st.session_state.show_add_url

        if st.session_state.show_add_url:
            with st.container(border=True):
                url = st.text_input("Enter URL to scan", placeholder="https://example.com")
                if st.button("🔍 Run Scan", type="primary"):
                    if url.strip():
                        with st.spinner("Scanning (desktop + mobile viewports)… takes ~30–60 seconds"):
                            result = call_secure_scan(url.strip())
                            if result:
                                save_to_history(url.strip(), result)
                                st.session_state.scan_results[url.strip()] = result
                                st.session_state.show_add_url = False
                                st.rerun()
                    else:
                        st.warning("Enter a URL first.")

        if not st.session_state.scan_results:
            st.info("🔎 No scans yet. Click **➕ Add URL** to begin.")
        else:
            # Charts
            all_rules = []
            for d in st.session_state.scan_results.values():
                all_rules.extend(d.get("rules",[]))

            if all_rules:
                df_all = pd.DataFrame(all_rules)
                auto   = df_all[df_all["test_type"]=="automated"]
                if not auto.empty:
                    c1,c2 = st.columns(2)
                    with c1:
                        sev_data = auto[auto["status"]=="fail"].groupby("severity").size().reset_index(name="count")
                        if not sev_data.empty:
                            fig = px.pie(sev_data, names="severity", values="count", hole=0.5,
                                         title="Failures by Severity",
                                         color="severity",
                                         color_discrete_map=SEV_COLORS)
                            st.plotly_chart(fig, use_container_width=True)
                    with c2:
                        scores = [{"URL":u[:40],"Score":calculate_score(pd.DataFrame(d.get("rules",[]))),"Failures":len([r for r in d.get("rules",[]) if r.get("status")=="fail"])}
                                  for u,d in st.session_state.scan_results.items()]
                        if scores:
                            fig2 = px.bar(pd.DataFrame(scores),x="URL",y="Score",title="Score per URL",
                                          color="Score",color_continuous_scale="RdYlGn",range_color=[0,100])
                            st.plotly_chart(fig2, use_container_width=True)

            st.divider()
            for url, result in st.session_state.scan_results.items():
                with st.container(border=True):
                    st.markdown(f"### {result.get('page_title') or url}")
                    st.caption(f"URL: {url} | Viewports: {', '.join(result.get('viewports_tested',['desktop']))}")

                    if "rules" not in result:
                        st.error("Scan failed."); continue

                    df = pd.DataFrame(result["rules"])
                    fails   = len(df[df["status"]=="fail"])
                    passed  = len(df[(df["status"]=="pass")&(df["test_type"]=="automated")])
                    review  = len(df[df["status"].isin(["manual","assisted"])])
                    score   = calculate_score(df)

                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("♿ Score",        f"{score}%")
                    c2.metric("🔴 Failures",     fails)
                    c3.metric("🟢 Passed",       passed)
                    c4.metric("🟠 Needs Review", review)

                    # Trend mini-chart
                    history = get_history(url)
                    if len(history) > 1:
                        hist_df = pd.DataFrame(reversed(history))
                        fig_trend = px.line(hist_df, x="scanned", y="score",
                                            title="Score trend", height=160,
                                            markers=True)
                        fig_trend.update_layout(showlegend=False, margin=dict(l=0,r=0,t=30,b=0))
                        st.plotly_chart(fig_trend, use_container_width=True)

                    a1,a2,a3 = st.columns(3)
                    if a1.button("📊 View Results", key=f"view_{url}"):
                        st.session_state.active_url = url
                        st.session_state.view = "results"; st.rerun()
                    a2.download_button(
                        "📄 Export PDF",
                        data=generate_pdf_report(url, result),
                        file_name=f"axessia_{url.replace('https://','').replace('/','_')[:50]}.pdf",
                        mime="application/pdf", key=f"pdf_{url}",
                    )
                    if a3.button("🗑️ Remove", key=f"del_{url}"):
                        del st.session_state.scan_results[url]; st.rerun()

    # ── SITE CRAWL ────────────────────────────────────
    else:
        st.subheader("🕷️ Site Crawl")
        st.caption("Axessia discovers all sections automatically and scans multiple pages.")

        with st.container(border=True):
            crawl_seed = st.text_input("Seed URL", placeholder="https://example.com", key="crawl_seed")
            max_pages  = st.slider("Max pages per section", 1, 5, 2, key="crawl_max")
            if st.button("🕷️ Start Crawl", type="primary", key="crawl_btn"):
                if not crawl_seed.strip(): st.error("Enter a seed URL.")
                else:
                    with st.spinner("Crawling… this may take 2–3 minutes."):
                        try:
                            resp = requests.post(
                                CRAWL_URL,
                                headers={"Content-Type":"application/json","x-api-key":API_KEY},
                                json={"seed_url":crawl_seed.strip(),"max_pages_per_section":max_pages},
                                timeout=300,
                            )
                            if resp.status_code == 200:
                                st.session_state.crawl_results = resp.json(); st.rerun()
                            else:
                                st.error(f"Crawl failed: HTTP {resp.status_code}")
                        except Exception as e:
                            st.error(f"Crawl error: {e}")

        if st.session_state.crawl_results:
            crawl_data = st.session_state.crawl_results
            sections   = crawl_data.get("sections",{})
            if sections:
                total_pages = sum(len(s.get("pages",[])) for s in sections.values())
                total_fails = sum(sum(1 for r in (s.get("rules") or []) if r.get("status")=="fail") for s in sections.values())
                avg_score   = round(sum(s.get("section_score",0) for s in sections.values())/len(sections),1)

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("📂 Sections",      len(sections))
                c2.metric("📄 Pages Scanned", total_pages)
                c3.metric("🔴 Total Failures",total_fails)
                c4.metric("♿ Avg Score",      f"{avg_score}%")
                st.divider()

                for sec_name, sec_data in sections.items():
                    risk  = sec_data.get("eaa_risk","Low")
                    score = sec_data.get("section_score",0)
                    pages = sec_data.get("pages",[])
                    rules = sec_data.get("rules") or []
                    fails = [r for r in rules if r.get("status")=="fail"]
                    risk_icon = {"High":"🔴","Medium":"🟠","Low":"🟢"}.get(risk,"🟡")

                    with st.container(border=True):
                        col1,col2,col3 = st.columns([4,2,2])
                        col1.markdown(f"### 📁 {sec_name}")
                        col1.caption(f"{len(pages)} page(s)")
                        col2.metric("Score", f"{score}%")
                        col3.metric("EAA Risk", f"{risk_icon} {risk}")
                        if fails:
                            with st.expander(f"🔴 {len(fails)} failure(s)"):
                                for r in fails[:10]:
                                    st.markdown(f"- **{r.get('name')}** — WCAG {r.get('wcag')} · {r.get('severity')}")
                        for pg in pages: st.caption(f"  • {pg}")

                if st.button("🗑️ Clear Crawl Results", key="clear_crawl"):
                    st.session_state.crawl_results = None; st.rerun()

# ══════════════════════════════════════════════════════
# RESULTS VIEW
# ══════════════════════════════════════════════════════
if st.session_state.view == "results":
    url    = st.session_state.active_url
    data   = st.session_state.scan_results.get(url,{})

    if not data or "rules" not in data:
        st.error("No results. Go back and run a scan.")
        if st.button("← Back"): st.session_state.view = "dashboard"; st.rerun()
        st.stop()

    df = pd.DataFrame(data["rules"])

    if st.button("← Back to Dashboard"):
        st.session_state.view = "dashboard"; st.session_state.active_url = None; st.rerun()

    page_title = data.get("page_title") or url
    st.markdown(f"## {page_title}")
    st.caption(f"`{url}` | Viewports: {', '.join(data.get('viewports_tested',['desktop']))}")

    tabs = st.tabs([
        "📊 Overview",
        "📋 WCAG Issues",
        "🔴 Failures + Screenshots",
        "🟠 Manual & Assisted",
        "🛠️ AI Dev Agent",
        "🧪 AI QA Agent",
        "⌨️ Keyboard / Focus",
        "🎨 Colour Analysis",
        "⚡ Dynamic Content",
        "📄 PDF Accessibility",
        "🔄 Regression",
        "⚖️ EAA Readiness",
    ])

    # ── Overview ─────────────────────────────────────
    with tabs[0]:
        fails   = len(df[df["status"]=="fail"])
        passed  = len(df[(df["status"]=="pass")&(df["test_type"]=="automated")])
        review  = len(df[df["status"].isin(["manual","assisted"])])
        score   = calculate_score(df)
        total_i = int(df[df["status"]=="fail"]["instance_count"].sum()) if "instance_count" in df.columns else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("♿ Score",          f"{score}%")
        c2.metric("🔴 Failures",       fails)
        c3.metric("🟢 Passed",         passed)
        c4.metric("🟠 Needs Review",   review)
        c5.metric("🔢 Total Instances",total_i)

        # Charts
        col1,col2 = st.columns(2)
        with col1:
            sev_data = df[df["status"]=="fail"].groupby("severity").size().reset_index(name="count")
            if not sev_data.empty:
                fig = px.pie(sev_data, names="severity", values="count", hole=0.5,
                             title="Failures by Severity", color="severity",
                             color_discrete_map=SEV_COLORS)
                st.plotly_chart(fig, use_container_width=True)
        with col2:
            wcag_data = df[df["status"]=="fail"].groupby("wcag")["instance_count"].sum().reset_index()
            wcag_data.columns = ["WCAG","Instances"]
            if not wcag_data.empty:
                fig2 = px.bar(wcag_data.sort_values("Instances", ascending=False).head(15),
                              x="WCAG", y="Instances", title="Failures by WCAG Criterion",
                              color="Instances", color_continuous_scale="Reds")
                st.plotly_chart(fig2, use_container_width=True)

        # Page screenshot comparison
        ps = data.get("page_screenshot")
        ms = data.get("mobile_screenshot")
        if ps or ms:
            st.markdown("### Page Screenshots")
            sc1,sc2 = st.columns(2)
            if ps:
                with sc1:
                    show_screenshot(ps, "Desktop (1280px)")
            if ms:
                with sc2:
                    show_screenshot(ms, "Mobile (375px)")

        # Score trend
        history = get_history(url)
        if len(history) > 1:
            st.markdown("### Score Trend")
            hist_df = pd.DataFrame(reversed(history))
            hist_df["scanned"] = pd.to_datetime(hist_df["scanned"]).dt.strftime("%m-%d %H:%M")
            fig3 = px.line(hist_df, x="scanned", y="score", markers=True,
                           title="Score over time", range_y=[0,100])
            fig3.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Target 80%")
            st.plotly_chart(fig3, use_container_width=True)

    # ── WCAG Issues table ─────────────────────────────
    with tabs[1]:
        t = df.copy()
        t["Confidence"] = t["test_type"].map(CONFIDENCE_LABELS)
        cols_show = ["name","wcag","level","severity","status","Confidence","instance_count"]
        existing  = [c for c in cols_show if c in t.columns]
        st.dataframe(
            t[existing].rename(columns={"instance_count":"Instances","name":"Rule"}),
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "📥 Download CSV",
            data=t[existing].to_csv(index=False),
            file_name="axessia_wcag_report.csv", mime="text/csv",
        )

    # ── Failures + Screenshots ────────────────────────
    with tabs[2]:
        failed = df[df["status"]=="fail"].copy()
        if failed.empty:
            st.success("🎉 No failures detected on this page!")
        else:
            # Filter controls
            sev_filter = st.multiselect(
                "Filter by severity",
                options=["critical","serious","moderate","minor"],
                default=["critical","serious","moderate","minor"],
                key="sev_filter",
            )
            vp_filter = st.selectbox(
                "Viewport", ["All","desktop","mobile"], key="vp_filter"
            )

            filtered = failed[failed["severity"].isin(sev_filter)]
            if vp_filter != "All" and "viewport" in filtered.columns:
                filtered = filtered[filtered["viewport"]==vp_filter]

            sev_order = {"critical":0,"serious":1,"moderate":2,"minor":3}
            filtered  = filtered.copy()
            filtered["_ord"] = filtered["severity"].map(sev_order)
            filtered  = filtered.sort_values(["_ord","instance_count"], ascending=[True,False])

            for _, row in filtered.iterrows():
                ai       = safe_ai(row.get("ai_explanation"))
                insts    = row.get("instances",[]) or []
                contrast = row.get("contrast_ratio")

                sev_c = SEV_COLORS.get(row.get("severity","moderate"),"#888")
                with st.expander(
                    f"{'🔴' if row['severity']=='critical' else '🟠' if row['severity']=='serious' else '🟡'} "
                    f"**{row['name']}** — WCAG {row.get('wcag','—')} | {row['severity'].upper()} | "
                    f"{row.get('instance_count',0)} instance(s) | {row.get('viewport','desktop')}"
                ):
                    c1,c2 = st.columns([3,1])
                    with c1:
                        if ai.get("user_impact"):
                            st.markdown("**User impact**"); st.write(ai["user_impact"])
                        if ai.get("dev_action"):
                            st.markdown("**Developer action**"); st.info(ai["dev_action"])
                        if ai.get("eaa_context"):
                            st.markdown("**EAA context**"); st.write(ai["eaa_context"])
                    with c2:
                        # Contrast ratio
                        if contrast:
                            actual   = contrast.get("actual","—")
                            required = contrast.get("required", 4.5)
                            st.metric(
                                "Contrast ratio",
                                f"{actual}:1",
                                delta=f"Required {required}:1",
                                delta_color="inverse",
                            )
                            st.caption(f"FG: {contrast.get('fg_color','—')} | BG: {contrast.get('bg_color','—')}")

                    # Failing instances + screenshots
                    if insts:
                        st.markdown(f"**{len(insts)} failing instance(s):**")
                        for j, inst in enumerate(insts[:10], 1):
                            with st.container(border=True):
                                cols = st.columns([3,2])
                                with cols[0]:
                                    snippet = inst.get("snippet","")
                                    if snippet:
                                        st.markdown(f"*Instance {j} — HTML:*")
                                        st.code(snippet[:400], language="html")
                                    fail_sum = inst.get("failure_summary","")
                                    if fail_sum:
                                        st.caption(f"❌ {fail_sum}")
                                with cols[1]:
                                    b64 = inst.get("screenshot_b64")
                                    if b64:
                                        show_screenshot(b64, f"Instance {j}")
                                    else:
                                        selector = inst.get("selector","")
                                        if selector:
                                            st.caption(f"Selector: `{selector}`")

                    # Help URL
                    if row.get("help_url"):
                        st.markdown(f"[WCAG Reference]({row['help_url']})")

                    # Create Defect button
                    st.markdown(
                        '<button style="background:transparent;border:1.5px solid #C8196E;'
                        'color:#C8196E;padding:6px 16px;border-radius:8px;font-size:0.85rem;'
                        'font-weight:600;cursor:pointer;margin-top:8px;">'
                        '🧾 Create Defect</button>',
                        unsafe_allow_html=True,
                    )

    # ── Manual & Assisted ─────────────────────────────
    with tabs[3]:
        review_df = df[df["status"].isin(["manual","assisted"])]
        if review_df.empty:
            st.success("No manual or assisted checks required.")
        for _, row in review_df.iterrows():
            ai    = safe_ai(row.get("ai_explanation"))
            label = CONFIDENCE_LABELS.get(row.get("test_type","manual"), row.get("test_type",""))
            with st.expander(f"{label} — **{row['name']}** | WCAG {row.get('wcag','—')} | {row.get('severity','').upper()}"):
                if ai.get("why_not_automated"):
                    st.markdown("**Why automation cannot determine this**"); st.write(ai["why_not_automated"])
                steps = ai.get("qa_steps", [])
                if steps:
                    st.markdown("**How to test manually:**")
                    if isinstance(steps, list):
                        for s in steps: st.write(f"— {s}")
                    else:
                        st.write(steps)
                if row.get("help_url"): st.markdown(f"[WCAG Reference]({row['help_url']})")

    # ── AI Dev Agent ──────────────────────────────────
    with tabs[4]:
        failed_dev = df[df["status"]=="fail"]
        if failed_dev.empty:
            st.success("No failures to fix.")
        for _, row in failed_dev.iterrows():
            ai    = safe_ai(row.get("ai_explanation"))
            insts = row.get("instances",[]) or []
            with st.expander(f"🛠️ Fix: **{row['name']}** ({row.get('wcag','—')}) — {row.get('instance_count',0)} instance(s)"):
                if insts and insts[0].get("snippet"):
                    st.markdown("**Failing HTML:**")
                    st.code(insts[0]["snippet"][:500], language="html")
                if ai.get("dev_action"):
                    st.markdown("**Required developer action:**"); st.info(ai["dev_action"])
                if row.get("contrast_ratio"):
                    cr = row["contrast_ratio"]
                    st.markdown(f"**Contrast:** {cr.get('actual','—')}:1 | Required: {cr.get('required',4.5)}:1 | FG: {cr.get('fg_color')} | BG: {cr.get('bg_color')}")
                if row.get("help_url"): st.markdown(f"[WCAG {row.get('wcag')} Reference]({row['help_url']})")

    # ── AI QA Agent ───────────────────────────────────
    with tabs[5]:
        review_items = df[df["status"].isin(["manual","assisted","fail"])]
        rows = []
        for _, r in review_items.iterrows():
            ai    = safe_ai(r.get("ai_explanation"))
            steps = ai.get("qa_steps",[])
            rows.append({
                "Rule":       r["name"],
                "WCAG":       r.get("wcag","—"),
                "Severity":   r.get("severity",""),
                "Type":       CONFIDENCE_LABELS.get(r.get("test_type",""),r.get("test_type","")),
                "Test Steps": " → ".join(steps) if isinstance(steps,list) else str(steps),
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No manual or failed rules to review.")

    # ── Keyboard / Focus ──────────────────────────────
    with tabs[6]:
        focus = data.get("focus_analysis",{})
        if not focus or not focus.get("success"):
            st.info("Focus analysis not available for this scan.")
        else:
            st.markdown("### Keyboard Tab Navigation Analysis")
            fc1,fc2,fc3 = st.columns(3)
            fc1.metric("Tab stops found",  focus.get("tab_count",0))
            fc2.metric("Focus trap",       "⚠️ YES" if focus.get("focus_trap") else "✅ No")
            fc3.metric("Invisible focus",  len(focus.get("invisible_focus",[])))

            if focus.get("focus_trap"):
                st.error("🔴 Focus trap detected — keyboard users cannot navigate away from a component.")

            invisible = focus.get("invisible_focus",[])
            if invisible:
                st.warning(f"⚠️ {len(invisible)} element(s) receive focus but are not visible to sighted users.")
                for el in invisible[:5]:
                    st.code(el.get("outerHTML",""), language="html")

            seq = focus.get("focus_sequence",[])
            if seq:
                st.markdown("### Tab Order Sequence")
                tab_rows = []
                for i, el in enumerate(seq, 1):
                    tab_rows.append({
                        "#":      i,
                        "Tag":    el.get("tag",""),
                        "Text":   el.get("text","")[:50],
                        "Role":   el.get("role",""),
                        "Visible":  "✅" if el.get("visible") else "❌",
                    })
                st.dataframe(pd.DataFrame(tab_rows), use_container_width=True, hide_index=True)

    # ── EAA Readiness ─────────────────────────────────
    with tabs[7]:
        from eaa_mapping import evaluate_eaa
        eaa = evaluate_eaa(data.get("rules",[]))

        risk      = eaa.get("risk_level","—")
        risk_map  = {"HIGH":"🔴","MEDIUM":"🟠","REVIEW":"🟡","LOW":"🟢"}
        risk_icon = risk_map.get(risk,"⚪")

        st.markdown(f"### EAA Readiness: {risk_icon} {risk}")
        ec1,ec2,ec3,ec4 = st.columns(4)
        ec1.metric("EAA Ready",           "✅ YES" if eaa.get("eaa_ready") else "❌ NO")
        ec2.metric("Critical failures",   eaa.get("failed_critical_count",0))
        ec3.metric("Other AA failures",   eaa.get("failed_aa_count",0))
        ec4.metric("Automated pass rate", f"{eaa.get('automated_pass_rate',0)}%")

        if eaa.get("blocking_wcag"):
            st.error(f"**Blocking criteria:** {', '.join(eaa['blocking_wcag'])}")

        if eaa.get("failed_critical"):
            st.markdown("### Critical EAA Failures")
            for f in eaa["failed_critical"]:
                st.markdown(
                    f"- **WCAG {f['wcag']}** — {f['name']} | "
                    f"{f.get('severity','').upper()} | "
                    f"{f.get('instance_count',0)} instance(s)"
                )

        if eaa.get("manual_review_items"):
            st.markdown("### Manual Review Required for EAA")
            for m in eaa["manual_review_items"]:
                st.markdown(f"- WCAG {m['wcag']} — {m['name']} ({m['test_type']})")

        st.info(
            "EAA (European Accessibility Act) requires compliance with EN 301 549, "
            "which references WCAG 2.1 Level AA as the standard for digital products in the EU. "
            "All Level A and AA criteria must pass to be EAA compliant."
        )

    # ── Colour Analysis ───────────────────────────────
    with tabs[7]:
        colour_data = data.get("colour_analysis")
        if not colour_data:
            st.info("Colour analysis not available. Re-run scan to include it.")
        else:
            summary = colour_data.get("summary", {})
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Colour combinations", summary.get("total_combinations",0))
            c2.metric("Failing contrast",    summary.get("failing",0))
            c3.metric("Passing contrast",    summary.get("passing",0))
            c4.metric("Pass rate",           f"{summary.get('pass_rate',0)}%")

            failures_c = colour_data.get("failures",[])
            if failures_c:
                st.markdown("### ❌ Contrast Failures")
                rows = []
                for f in failures_c[:30]:
                    rows.append({
                        "FG Colour":  f["fg"],
                        "BG Colour":  f["bg"],
                        "Ratio":      f"{f['ratio']}:1",
                        "Required":   f"{f['required']}:1",
                        "Element":    f.get("element",""),
                        "Text":       f.get("text","")[:40],
                        "Large Text": "Yes" if f.get("is_large") else "No",
                    })
                if rows:
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Colour palette
            palette = colour_data.get("palette",[])
            if palette:
                st.markdown("### 🎨 Colour Palette Used on Page")
                cols_per_row = 8
                cols = st.columns(cols_per_row)
                for i, colour in enumerate(palette[:40]):
                    with cols[i % cols_per_row]:
                        st.markdown(
                            f'<div style="width:36px;height:36px;background:{colour};border-radius:6px;border:1px solid #ddd;"></div>'
                            f'<div style="font-size:9px;color:#888;margin-top:2px;">{colour}</div>',
                            unsafe_allow_html=True,
                        )

    # ── Dynamic Content ───────────────────────────────
    with tabs[8]:
        dynamic = data.get("dynamic_findings",[])
        if not dynamic:
            if "dynamic_findings" not in data:
                st.info("Dynamic content scan not run. Re-scan to include SPA/dynamic content testing.")
            else:
                st.success("✅ No additional failures found in dynamic content (modals, dropdowns, accordions).")
        else:
            st.warning(f"⚠️ {len(dynamic)} additional violations found only in dynamic states (not visible on initial page load).")
            for finding in dynamic:
                with st.expander(
                    f"💬 Triggered by: **{finding.get('trigger_element','?')}** → "
                    f"**{finding.get('violation_name','?')}** ({finding.get('impact','?').upper()})"
                ):
                    st.markdown(f"**Trigger element HTML:**")
                    st.code(finding.get("trigger_html",""), language="html")
                    st.markdown(f"**Violation:** `{finding.get('violation_id')}` | WCAG {finding.get('wcag','—')}")
                    st.markdown("**What happens:** This violation only appears after a user interaction (e.g. opening a modal, dropdown or accordion). Automated scanners that don't interact with the page will miss it.")
                    b64 = finding.get("screenshot_b64")
                    if b64: show_screenshot(b64, f"Dynamic state when '{finding.get('trigger_element','?')}' is open")
                    if finding.get("nodes"):
                        st.markdown("**Failing HTML in dynamic state:**")
                        for node in finding["nodes"][:2]:
                            st.code(node.get("html",""), language="html")

    # ── PDF Accessibility ─────────────────────────────
    with tabs[9]:
        pdf_data = data.get("pdf_analysis")
        if not pdf_data:
            if "pdf_analysis" not in data:
                st.info("PDF accessibility check not run. Re-scan to include it.")
            else:
                st.info("No PDF files linked from this page.")
        else:
            summary_p = pdf_data.get("summary",{})
            pc1,pc2,pc3 = st.columns(3)
            pc1.metric("PDF files found",   summary_p.get("total",0))
            pc2.metric("With issues",        summary_p.get("with_issues",0))
            pc3.metric("Checked",            summary_p.get("checked",0))

            for pdf in pdf_data.get("pdfs",[]):
                with st.expander(f"📄 {pdf.get('link_text') or pdf.get('url','PDF')[:60]}"):
                    st.caption(pdf.get("url",""))
                    if pdf.get("error"):
                        st.error(f"Could not check: {pdf['error']}")
                    else:
                        if pdf.get("pages"):  st.caption(f"{pdf['pages']} pages | {pdf.get('file_size','?')}")
                        rules = pdf.get("rules",[])
                        for rule in rules:
                            icon = "✅" if rule.get("status")=="pass" else "❌"
                            st.markdown(f"{icon} **{rule.get('name')}** (WCAG {rule.get('wcag','—')} | {rule.get('severity','').upper()})")
                            if rule.get("detail"):
                                st.caption(rule["detail"])

    # ── Regression ────────────────────────────────────
    with tabs[10]:
        from regression_tracker import compare_scans, get_previous_snapshot
        prev = get_previous_snapshot(url)
        regression = compare_scans(data, prev)

        if not regression.get("has_previous"):
            st.info("This is the first scan for this URL. Run again to see regression tracking (NEW vs FIXED vs EXISTING).")
        else:
            st.caption(f"Compared against scan from: {regression.get('previous_scan','?')} | Previous score: {regression.get('previous_score','?')}%")
            rc1,rc2,rc3 = st.columns(3)
            rc1.metric("🆕 New failures",      regression.get("new_count",0),     delta=str(regression.get("new_count",0)), delta_color="inverse")
            rc2.metric("🔁 Existing failures",  regression.get("existing_count",0))
            rc3.metric("✅ Fixed since last scan",regression.get("fixed_count",0), delta=str(regression.get("fixed_count",0)), delta_color="normal")

            if regression.get("new"):
                st.markdown("### 🆕 New Failures (appeared since last scan)")
                for r in regression["new"]:
                    st.error(f"NEW: **{r.get('name')}** — WCAG {r.get('wcag','—')} | {r.get('severity','').upper()} | {r.get('instance_count',0)} instance(s)")

            if regression.get("fixed"):
                st.markdown("### ✅ Fixed Since Last Scan")
                for r in regression["fixed"]:
                    st.success(f"FIXED: **{r.get('name',r.get('id','?'))}**")

            if regression.get("existing"):
                with st.expander(f"🔁 {regression.get('existing_count',0)} existing failures (unchanged since last scan)"):
                    for r in regression["existing"]:
                        st.warning(f"EXISTING: **{r.get('name')}** — WCAG {r.get('wcag','—')} | {r.get('instance_count',0)} instance(s)")
