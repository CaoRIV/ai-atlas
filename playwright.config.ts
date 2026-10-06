import { defineConfig } from "@playwright/test";

const baseURL = process.env.DISCOVER_BASE_URL;
const outputDir = process.env.E2E_PLAYWRIGHT_OUTPUT_DIR;

if (!baseURL || !outputDir) {
  throw new Error("Use `pnpm test:e2e:discover` so the isolated E2E stack is configured.");
}

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: "line",
  outputDir,
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL,
    browserName: "chromium",
    headless: true,
    navigationTimeout: 20_000,
    actionTimeout: 10_000,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
});
