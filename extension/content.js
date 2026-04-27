// content.js — Axessia Extension Content Script
// Runs on every page — listens for scan requests from popup

const AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.0/axe.min.js";

function injectAxe() {
  return new Promise((resolve) => {
    if (typeof axe !== "undefined") { resolve(); return; }
    const script  = document.createElement("script");
    script.src    = AXE_CDN;
    script.onload = resolve;
    script.onerror= resolve;
    document.head.appendChild(script);
  });
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "RUN_AXE") {
    injectAxe().then(() => {
      if (typeof axe === "undefined") {
        sendResponse({ error: "axe-core failed to load" });
        return;
      }
      axe.run(document).then(results => {
        sendResponse({ results });
      }).catch(err => {
        sendResponse({ error: err.message });
      });
    });
    return true; // async
  }
});
