// popup.js — Axessia Chrome Extension

const AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js";

let scanResults = null;
let currentTabUrl = "";

const statusBar      = document.getElementById("statusBar");
const resultsSection = document.getElementById("resultsSection");
const scanBtn        = document.getElementById("scanBtn");
const sendBtn        = document.getElementById("sendBtn");
const dashInput      = document.getElementById("dashboardUrl");
const apiKeyInput    = document.getElementById("apiKey");
const urlDisplay     = document.getElementById("currentUrl");

// Load saved settings
chrome.storage.local.get(["dashboardUrl", "apiKey"], (data) => {
  if (data.dashboardUrl) dashInput.value = data.dashboardUrl;
  if (data.apiKey)       apiKeyInput.value = data.apiKey;
});

// Save settings on change
dashInput.addEventListener("change", () => {
  chrome.storage.local.set({ dashboardUrl: dashInput.value });
});
apiKeyInput.addEventListener("change", () => {
  chrome.storage.local.set({ apiKey: apiKeyInput.value });
});

// Get current tab URL
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs[0]) {
    currentTabUrl = tabs[0].url;
    urlDisplay.textContent = currentTabUrl.length > 55
      ? currentTabUrl.substring(0, 55) + "…"
      : currentTabUrl;
  }
});

function setStatus(msg, type = "") {
  statusBar.textContent = msg;
  statusBar.className   = `status ${type}`;
  statusBar.style.display = "block";
}

function renderResults(violations, passes) {
  const total    = violations.length + passes.length;
  const score    = total > 0 ? Math.round((passes.length / total) * 100) : 100;

  const sevCounts = { critical: 0, serious: 0, moderate: 0, minor: 0 };
  violations.forEach(v => {
    const sev = v.impact || "moderate";
    if (sevCounts[sev] !== undefined) sevCounts[sev]++;
  });

  let html = `
    <div class="metric"><span class="metric-label">Score</span><span class="metric-value val-score">${score}%</span></div>
    <div class="metric"><span class="metric-label">Failures</span><span class="metric-value val-fail">${violations.length}</span></div>
    <div class="metric"><span class="metric-label">Critical</span><span class="metric-value val-fail">${sevCounts.critical}</span></div>
    <div class="metric"><span class="metric-label">Serious</span><span class="metric-value" style="color:#EF9F27">${sevCounts.serious}</span></div>
    <div class="metric"><span class="metric-label">Passed</span><span class="metric-value val-pass">${passes.length}</span></div>
  `;

  if (violations.length > 0) {
    html += `<div class="violations">`;
    violations.slice(0, 15).forEach(v => {
      const sev = v.impact || "moderate";
      html += `
        <div class="violation">
          <span class="vio-name">${v.help || v.id}</span>
          <span class="vio-sev sev-${sev}">${sev.toUpperCase()}</span>
          <div style="color:#888;font-size:10px;margin-top:2px;">WCAG ${(v.tags||[]).find(t=>t.includes('.')) || '—'} · ${v.nodes?.length||0} instance(s)</div>
        </div>
      `;
    });
    if (violations.length > 15) {
      html += `<div style="text-align:center;color:#888;padding:4px;">+${violations.length - 15} more violations</div>`;
    }
    html += `</div>`;
  } else {
    html += `<div style="color:#1D9E75;font-weight:700;padding:8px 0;text-align:center;">🎉 No failures detected!</div>`;
  }

  resultsSection.innerHTML = html;
  resultsSection.style.display = "block";
}

// SCAN button
scanBtn.addEventListener("click", async () => {
  scanResults = null;
  sendBtn.disabled = true;
  resultsSection.style.display = "none";
  setStatus("Injecting axe-core…", "running");
  scanBtn.disabled = true;

  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    // Inject axe-core
    await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (cdnUrl) => {
        return new Promise((resolve) => {
          if (typeof axe !== "undefined") { resolve(); return; }
          const s = document.createElement("script");
          s.src = cdnUrl;
          s.onload = resolve;
          document.head.appendChild(s);
        });
      },
      args: [AXE_CDN],
    });

    setStatus("Running accessibility scan…", "running");

    // Run axe
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => axe.run(document),
    });

    scanResults = result;
    const violations = result.violations || [];
    const passes     = result.passes     || [];

    renderResults(violations, passes);
    setStatus(`Scan complete — ${violations.length} failure(s) found`, violations.length > 0 ? "error" : "done");
    sendBtn.disabled = false;

  } catch (err) {
    setStatus(`Scan failed: ${err.message}`, "error");
  } finally {
    scanBtn.disabled = false;
  }
});

// SEND TO DASHBOARD button
sendBtn.addEventListener("click", async () => {
  if (!scanResults) return;

  const dashUrl = dashInput.value.trim().replace(/\/$/, "");
  const apiKey  = apiKeyInput.value.trim();

  if (!dashUrl) { setStatus("Enter your Axessia dashboard URL first.", "error"); return; }
  if (!apiKey)  { setStatus("Enter your API key first.", "error"); return; }

  setStatus("Sending results to dashboard…", "running");
  sendBtn.disabled = true;

  try {
    const payload = {
      url:        currentTabUrl,
      violations: scanResults.violations || [],
      passes:     scanResults.passes     || [],
      source:     "chrome-extension",
      scanned_at: new Date().toISOString(),
    };

    const resp = await fetch(`${dashUrl}/ingest-extension`, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key":    apiKey,
      },
      body: JSON.stringify(payload),
    });

    if (resp.ok) {
      setStatus("✅ Results sent to Axessia dashboard!", "done");
      chrome.notifications.create({
        type:    "basic",
        iconUrl: "icons/icon48.png",
        title:   "Axessia — Scan Sent",
        message: `Results for ${currentTabUrl.substring(0,50)} sent to dashboard.`,
      });
    } else {
      setStatus(`Failed to send: HTTP ${resp.status}`, "error");
    }
  } catch (err) {
    setStatus(`Send failed: ${err.message}`, "error");
  } finally {
    sendBtn.disabled = false;
  }
});
