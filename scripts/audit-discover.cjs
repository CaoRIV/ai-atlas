// Opt-in accessibility/layout audit, not the TASK-007 journey E2E suite.
// Reads a seeded local app. Browser tools are supplied by the operator, not shipped at runtime.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

(async () => {
  const base = new URL(process.env.DISCOVER_BASE_URL || "http://127.0.0.1:3000");
  assert.ok(["127.0.0.1", "localhost", "[::1]"].includes(base.hostname), "Use a local test app.");
  const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");
  const axeEntry = require.resolve(process.env.AXE_CORE_MODULE || "axe-core");
  const axeSource = fs.readFileSync(path.join(path.dirname(axeEntry), "axe.min.js"), "utf8");
  const directory = path.resolve(".cache/discover-audit");
  fs.mkdirSync(directory, { recursive: true });
  const catalog = await fetch(`${base.origin}/api/catalog/tools?page_size=1`, {
    signal: AbortSignal.timeout(15000),
  });
  assert.ok(catalog.ok, "Catalog must be available.");
  const toolId = (await catalog.json()).data?.[0]?.id;
  assert.ok(toolId, "Import curated seed before auditing.");
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_EXECUTABLE || undefined });
  const report = { timestamp: new Date().toISOString(), browser: browser.version(), axe: null, results: [], pageErrors: [] };
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(15000);
    page.on("pageerror", error => report.pageErrors.push(error.message));
    await page.goto(base.origin);
    for (const locale of ["vi", "en"]) {
      for (const theme of ["dark", "light"]) {
        await page.evaluate(({ locale, theme }) => {
          localStorage.setItem("ai-atlas-locale", locale);
          localStorage.setItem("ai-atlas-theme", theme);
        }, { locale, theme });
        for (const width of [320, 360, 768, 1024, 1366, 1920]) {
          await page.setViewportSize({ width, height: 900 });
          for (const [name, route, ready] of [
            ["home", "/", ".tool-card:not(.tool-card-skeleton)"],
            ["explorer", "/explorer", ".tool-card:not(.tool-card-skeleton)"],
            ["detail", `/tools/${encodeURIComponent(toolId)}`, ".fact-row"],
          ]) {
            const response = await page.goto(base.origin + route);
            assert.equal(response.status(), 200);
            await page.locator(ready).first().waitFor();
            await page.waitForFunction(locale => document.documentElement.lang === locale, locale);
            await page.addScriptTag({ content: axeSource });
            const audit = await page.evaluate(async () => {
              const result = await axe.run();
              return {
                axe: axe.version,
                violations: result.violations,
                incomplete: result.incomplete,
                overflow: document.documentElement.scrollWidth > innerWidth,
              };
            });
            report.axe = audit.axe;
            report.results.push({ name, locale, theme, width, ...audit });
            if (width === 360 || width === 1366) {
              await page.screenshot({ path: path.join(directory, `${name}-${locale}-${theme}-${width}.png`), fullPage: true });
            }
          }
        }
        console.log(`Audited ${locale}/${theme}: 3 pages at 6 widths`);
      }
    }
  } finally {
    fs.writeFileSync(path.join(directory, "report.json"), JSON.stringify(report, null, 2));
    await browser.close();
  }
  assert.equal(report.results.length, 72);
  assert.deepEqual(report.pageErrors, []);
  assert.ok(report.results.every(result => !result.overflow && result.violations.length === 0), "Audit failed; see .cache/discover-audit/report.json");
  console.log(`PASS 72 scans; manual-review results: ${report.results.filter(result => result.incomplete.length).length}`);
})().catch(error => { console.error(error); process.exitCode = 1; });
