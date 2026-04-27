const { chromium } = require("playwright");
const axeCore = require("axe-core");

(async () => {
  const url = process.argv[2];
  if (!url) {
    console.error("URL required");
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto(url, { waitUntil: "load", timeout: 60000 });

  await page.addScriptTag({ content: axeCore.source });
  const results = await page.evaluate(async () => {
    return await axe.run();
  });

  await browser.close();

  console.log(JSON.stringify(results));
})();
