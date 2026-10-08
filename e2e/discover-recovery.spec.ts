import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const archived = JSON.parse(readFileSync("e2e/fixtures/archived-tool.json", "utf8")) as {
  id: string; slug: string; name: string; description: string; official_url: string;
};
const filteredPath = "/explorer?q=ChatGPT&category=chatting-assistants&pricing_model=unknown&sort=name";
const cards = (page: Page) => page.getByRole("link", { name: /^Xem chi tiết / });
const resultAlert = (page: Page) => page.getByRole("region", { name: "Kết quả", exact: true }).getByRole("alert");

function toolsQuery(url: string, query: string): boolean {
  const parsed = new URL(url);
  return parsed.pathname === "/api/catalog/tools" && parsed.searchParams.get("q") === query;
}

test("empty real results reset search and filters", async ({ page }) => {
  const response = page.waitForResponse((response) => toolsQuery(response.url(), "ChatGPT"));
  await page.goto("/explorer?q=ChatGPT&api_available=false");
  const empty = await response;
  expect(empty.status()).toBe(200);
  expect(await empty.json()).toMatchObject({ data: [], pagination: { total: 0 } });
  await expect(page.getByText("Không có công cụ phù hợp với tìm kiếm và bộ lọc hiện tại.")).toBeVisible();
  await expect(cards(page)).toHaveCount(0);
  await page.getByRole("button", { name: "Xóa tìm kiếm và bộ lọc" }).click();
  await expect(page).toHaveURL(/\/explorer$/);
  await expect(page.getByRole("searchbox", { name: "Tìm theo tên hoặc tác vụ" })).toHaveValue("");
  await expect(cards(page)).toHaveCount(15);
});

test("real invalid category returns 422 and reset restores the catalog", async ({ page }) => {
  const response = page.waitForResponse((response) => toolsQuery(response.url(), "ChatGPT"));
  await page.goto("/explorer?q=ChatGPT&category=missing-e2e-category");
  const invalid = await response;
  expect(invalid.status()).toBe(422);
  const body = await invalid.json();
  expect(body.request_id).toBeTruthy();
  await expect(resultAlert(page)).toContainText(body.request_id);
  await expect(resultAlert(page)).toContainText("Query hoặc bộ lọc trong URL không hợp lệ.");
  await expect(cards(page)).toHaveCount(0);
  await page.getByRole("button", { name: "Đặt lại tìm kiếm và bộ lọc" }).click();
  await expect(page).toHaveURL(/\/explorer$/);
  await expect(cards(page)).toHaveCount(15);
});

test("public 404 hides archived metadata in API, HTML and browser", async ({ request, page }) => {
  const detail = await request.get(`/api/catalog/tools/${archived.id}`);
  expect(detail.status()).toBe(404);
  const list = await request.get("/api/catalog/tools?page_size=100");
  expect(list.status()).toBe(200);
  const listed = await list.json();
  expect(listed.pagination.total).toBe(15);
  expect(listed.data.map((tool: { id: string }) => tool.id)).not.toContain(archived.id);
  const search = await request.get(`/api/catalog/tools?q=${encodeURIComponent(archived.name)}`);
  expect(search.status()).toBe(200);
  expect(await search.json()).toMatchObject({ data: [], pagination: { total: 0 } });
  for (const id of [archived.id, "not-a-uuid", "ffffffff-ffff-4fff-8fff-ffffffffffff"]) {
    const html = await request.get(`/tools/${id}`);
    expect(html.status()).toBe(404);
    const navigation = await page.goto(`/tools/${id}`);
    expect(navigation?.status()).toBe(404);
    await expect(page.getByRole("main")).toBeVisible();
    await expect(page.getByRole("link", { name: "Mở website chính thức" })).toHaveCount(0);
    for (const secret of [archived.name, archived.slug, archived.description, archived.official_url]) {
      expect(await detail.text()).not.toContain(secret);
      expect(await html.text()).not.toContain(secret);
      expect(await page.content()).not.toContain(secret);
      expect(await list.text()).not.toContain(secret);
    }
  }
});

test("503 preserves query and request ID then retries the real backend", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const requestId = "e2e-catalog-unavailable";
  let failedUrl = "";
  await page.route("**/api/catalog/tools?**", async (route) => {
    failedUrl = route.request().url();
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      headers: { "x-request-id": requestId },
      body: JSON.stringify({ error: { code: "CATALOG_UNAVAILABLE", message: "Unavailable", details: [] }, request_id: requestId }),
    });
  }, { times: 1 });
  await page.goto(filteredPath);
  await expect(resultAlert(page)).toContainText(requestId);
  await expect(resultAlert(page)).toContainText("Chưa thể tải kết quả lúc này.");
  expect(new URL(page.url()).pathname + new URL(page.url()).search).toBe(filteredPath);
  await expect(page.getByRole("searchbox", { name: "Tìm theo tên hoặc tác vụ" })).toHaveValue("ChatGPT");
  await expect(page.getByRole("checkbox", { name: "Chatting & Assistants" })).toBeChecked();
  await expect(page.getByRole("combobox", { name: "Sắp xếp" })).toHaveValue("name");
  const retry = page.waitForResponse((response) => response.url() === failedUrl);
  await page.getByRole("button", { name: "Thử lại" }).click();
  expect((await retry).status()).toBe(200);
  await expect(cards(page)).toHaveCount(1);
  await expect(page.getByRole("link", { name: "Xem chi tiết ChatGPT" })).toBeVisible();
  await expect(resultAlert(page)).toHaveCount(0);
  expect(new URL(page.url()).pathname + new URL(page.url()).search).toBe(filteredPath);
});

test("a delayed old search cannot overwrite the newer real result", async ({ page }) => {
  await page.goto("/explorer?q=Gemini");
  await expect(page.getByRole("link", { name: "Xem chi tiết Gemini", exact: true })).toBeVisible();
  let release!: () => void;
  let captured!: () => void;
  let settled!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const oldCaptured = new Promise<void>((resolve) => { captured = resolve; });
  const oldSettled = new Promise<void>((resolve) => { settled = resolve; });
  await page.route("**/api/catalog/tools?**", async (route) => {
    if (!toolsQuery(route.request().url(), "ChatGPT")) return route.continue();
    try {
      const realResponse = await route.fetch();
      expect(realResponse.status()).toBe(200);
      expect((await realResponse.json()).data.map((tool: { name: string }) => tool.name)).toEqual(["ChatGPT"]);
      captured();
      await gate;
      await route.fulfill({ response: realResponse });
    } finally {
      settled();
    }
  });
  const search = page.getByRole("searchbox", { name: "Tìm theo tên hoặc tác vụ" });
  try {
    await search.fill("ChatGPT");
    await search.press("Enter");
    await oldCaptured;
    await expect(page.getByRole("status")).toContainText("Đang cập nhật kết quả");
    await expect(page.getByRole("link", { name: "Xem chi tiết Gemini", exact: true })).toBeVisible();
    const cancelled = page.waitForEvent("requestfailed", (request) => toolsQuery(request.url(), "ChatGPT"));
    await search.fill("Claude");
    await search.press("Enter");
    await expect(page.getByRole("link", { name: "Xem chi tiết Claude", exact: true })).toBeVisible();
    await cancelled;
    release();
    await oldSettled;
    await page.evaluate(() => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    await expect(page).toHaveURL(/\/explorer\?q=Claude$/);
    await expect(cards(page)).toHaveCount(1);
    await expect(page.getByRole("link", { name: "Xem chi tiết Claude", exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Xem chi tiết ChatGPT", exact: true })).toHaveCount(0);
    await expect(resultAlert(page)).toHaveCount(0);
  } finally {
    release();
    await page.unrouteAll({ behavior: "wait" });
  }
});
