// background.js — Axessia Extension Service Worker

chrome.runtime.onInstalled.addListener(() => {
  console.log("Axessia Accessibility Scanner installed.");
});

// Handle messages from content.js or popup.js
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SEND_RESULTS") {
    sendResultsToDashboard(message.payload)
      .then(result => sendResponse({ success: true, result }))
      .catch(err  => sendResponse({ success: false, error: err.message }));
    return true; // keep channel open for async
  }
});

async function sendResultsToDashboard(payload) {
  const { dashboardUrl, apiKey } = await chrome.storage.local.get(["dashboardUrl", "apiKey"]);
  if (!dashboardUrl || !apiKey) {
    throw new Error("Dashboard URL and API key not configured.");
  }

  const url = dashboardUrl.replace(/\/$/, "") + "/ingest-extension";
  const resp = await fetch(url, {
    method:  "POST",
    headers: { "Content-Type": "application/json", "x-api-key": apiKey },
    body:    JSON.stringify(payload),
  });

  if (!resp.ok) {
    throw new Error(`HTTP ${resp.status}`);
  }
  return await resp.json();
}
