// Opt-in browser regression for the filter drawer; no network outside the local app.
// Requires a running seeded web/API and a locally installed Playwright + Chromium.
const assert = require("node:assert/strict");

async function checkDrawerFocus(page, baseUrl) {
  const labels = {
    en: { trigger: "Filters (0)", dialog: "Filters", close: "Close filters" },
    vi: { trigger: "Bộ lọc (0)", dialog: "Bộ lọc", close: "Đóng bộ lọc" },
  };
  await page.goto(baseUrl);
  for (const locale of ["vi", "en"]) {
    await page.evaluate(value => localStorage.setItem("ai-atlas-locale", value), locale);
    for (const width of [320, 360, 768, 1024]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto(`${baseUrl}/explorer`);
      await page.locator(".tool-card:not(.tool-card-skeleton)").first().waitFor();
      const text = labels[locale];
      const trigger = page.getByRole("button", { name: text.trigger, exact: true });
      await trigger.click();
      const dialog = page.getByRole("dialog", { name: text.dialog, exact: true });
      await dialog.getByRole("checkbox").first().waitFor();
      await dialog.getByRole("button", { name: text.close, exact: true }).focus();
      const visited = new Set();
      for (let step = 0; step < 40; step++) {
        await page.keyboard.press(step < 20 ? "Tab" : "Shift+Tab");
        const focus = await page.evaluate(() => {
          const element = document.activeElement;
          const rect = element.getBoundingClientRect();
          const hit = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
          return {
            inside: !!element.closest('[role="dialog"]'),
            visible: !!hit && (hit === element || element.contains(hit)),
            label: element.getAttribute("aria-label") || element.textContent,
            tag: element.tagName,
          };
        });
        assert.ok(focus.inside && focus.visible, `${locale}/${width}: ${JSON.stringify(focus)}`);
        visited.add(focus.tag);
      }
      assert.ok(visited.has("SELECT") && visited.has("INPUT") && visited.has("BUTTON"));
      await page.keyboard.press("Escape");
      assert.ok(await trigger.evaluate(element => element === document.activeElement));
      console.log(`PASS ${locale}/${width}: focus trapped, visible, restored`);
    }
  }
}

module.exports = { checkDrawerFocus };

if (require.main === module) {
  (async () => {
    const baseUrl = new URL(process.env.DISCOVER_BASE_URL || "http://127.0.0.1:3000");
    assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(baseUrl.hostname), "Use a local test app.");
    const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
    const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined });
    try {
      const page = await browser.newPage();
      page.setDefaultTimeout(15000);
      await checkDrawerFocus(page, baseUrl.origin);
    } finally {
      await browser.close();
    }
  })().catch(error => { console.error(error); process.exitCode = 1; });
}
