import { expect, test } from "@playwright/test";

const journeys = [
  {
    locale: "vi",
    homeHeading: "Tìm công cụ AI. Xây stack phù hợp.",
    homeSearch: "Bạn đang tìm công cụ nào?",
    homeSubmit: "Tìm công cụ",
    explorerHeading: "Khám phá công cụ AI",
    explorerSearch: "Tìm theo tên hoặc tác vụ",
    filters: "Bộ lọc",
    pricingFilter: "Mô hình giá",
    sort: "Sắp xếp",
    results: "1 kết quả",
    details: "Xem chi tiết",
    back: "Quay lại Explorer",
    capability: "Text generation",
    verified: "Đã xác minh",
    pricingFact: "Giá",
    unknown: "Chưa có dữ liệu",
    sources: "Xem nguồn (1)",
    checked: /^Kiểm tra:/,
    expires: /^Hết hiệu lực:/,
    official: "Mở website chính thức",
    pageOne: "Trang 1 / 1",
  },
  {
    locale: "en",
    homeHeading: "Find AI tools. Build the right stack.",
    homeSearch: "What kind of tool are you looking for?",
    homeSubmit: "Find tools",
    explorerHeading: "Explore AI tools",
    explorerSearch: "Search by name or task",
    filters: "Filters",
    pricingFilter: "Pricing model",
    sort: "Sort",
    results: "1 result",
    details: "View details",
    back: "Back to Explorer",
    capability: "Text generation",
    verified: "Verified",
    pricingFact: "Pricing",
    unknown: "No data yet",
    sources: "View sources (1)",
    checked: /^Checked:/,
    expires: /^Expires:/,
    official: "Open official website",
    pageOne: "Page 1 of 1",
  },
] as const;

const canonicalExplorerPath =
  "/explorer?q=ChatGPT&category=chatting-assistants&pricing_model=unknown";

for (const journey of journeys) {
  test(`completes Journey A in ${journey.locale}`, async ({ context, page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto("/");

    const initialLocale = page.getByRole("combobox", { name: "Ngôn ngữ" });
    await expect(initialLocale).toHaveValue("vi");
    if (journey.locale === "en") {
      await initialLocale.selectOption("en");
      await expect(page.getByRole("combobox", { name: "Language" })).toHaveValue("en");
    }
    await expect(page.getByRole("heading", { level: 1, name: journey.homeHeading })).toBeVisible();

    await page.getByRole("searchbox", { name: journey.homeSearch }).fill("ChatGPT");
    await page.getByRole("button", { name: journey.homeSubmit }).click();
    await expect(page).toHaveURL(/\/explorer\?q=ChatGPT$/);
    await expect(
      page.getByRole("heading", { level: 1, name: journey.explorerHeading }),
    ).toBeVisible();

    const filterRail = page.getByRole("complementary", { name: journey.filters });
    await filterRail.getByRole("checkbox", { name: "Chatting & Assistants" }).click();
    await expect(page).toHaveURL(/q=ChatGPT&category=chatting-assistants$/);
    await expect(
      page
        .getByRole("complementary", { name: journey.filters })
        .getByRole("checkbox", { name: "Chatting & Assistants" }),
    ).toBeChecked();
    await filterRail
      .getByRole("combobox", { name: journey.pricingFilter })
      .selectOption("unknown");
    await expect(page).toHaveURL(new RegExp(`${canonicalExplorerPath.replaceAll("?", "\\?")}$`));

    await expect(page.getByText(journey.results, { exact: true })).toBeVisible();
    const detailLink = page.getByRole("link", { name: `${journey.details} ChatGPT` });
    await expect(detailLink).toBeVisible();
    await detailLink.click();

    await expect(page.getByRole("heading", { level: 1, name: "ChatGPT" })).toBeVisible();
    await expect(page.getByText("OpenAI", { exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: journey.capability })).toBeVisible();
    await expect(page.getByText(journey.verified, { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: journey.pricingFact, exact: true })).toBeVisible();
    await expect(page.getByText(journey.unknown, { exact: true }).first()).toBeVisible();

    await page.getByText(journey.sources, { exact: true }).first().click();
    await expect(page.getByRole("link", { name: /help\.openai\.com/ }).first()).toBeVisible();
    await expect(page.getByText(journey.checked).first()).toContainText("2026");
    await expect(page.getByText(journey.expires).first()).toContainText("2026");

    const detailUrl = new URL(page.url());
    expect(detailUrl.pathname).toBe("/tools/f834b059-14a7-54b3-9262-5ed5c5d65f67");
    expect(detailUrl.searchParams.get("from")).toBe(canonicalExplorerPath);

    await page.getByRole("link", { name: journey.back }).click();
    await expect(page).toHaveURL(new RegExp(`${canonicalExplorerPath.replaceAll("?", "\\?")}$`));
    await expect(page.getByRole("searchbox", { name: journey.explorerSearch })).toHaveValue(
      "ChatGPT",
    );
    const restoredFilters = page.getByRole("complementary", { name: journey.filters });
    await expect(
      restoredFilters.getByRole("checkbox", { name: "Chatting & Assistants" }),
    ).toBeChecked();
    await expect(
      restoredFilters.getByRole("combobox", { name: journey.pricingFilter }),
    ).toHaveValue("unknown");
    await expect(page.getByRole("combobox", { name: journey.sort })).toHaveValue("relevance");
    await expect(page.getByText(journey.pageOne, { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: `${journey.details} ChatGPT` })).toBeVisible();

    await page.getByRole("link", { name: `${journey.details} ChatGPT` }).click();
    const officialLink = page.getByRole("link", { name: journey.official });
    await expect(officialLink).toHaveAttribute("href", "https://chatgpt.com/");
    await expect(officialLink).toHaveAttribute("target", "_blank");
    await expect(officialLink).toHaveAttribute("rel", /\bnoopener\b/);
    await expect(officialLink).toHaveAttribute("rel", /\bnoreferrer\b/);

    let interceptedOfficialRequests = 0;
    await context.route("https://chatgpt.com/**", async (route) => {
      interceptedOfficialRequests += 1;
      await route.fulfill({
        body: "<!doctype html><html><body><h1>Intercepted official website</h1></body></html>",
        contentType: "text/html",
        status: 200,
      });
    });
    const [officialPage] = await Promise.all([page.waitForEvent("popup"), officialLink.click()]);
    await expect(
      officialPage.getByRole("heading", { name: "Intercepted official website" }),
    ).toBeVisible();
    await expect(officialPage).toHaveURL("https://chatgpt.com/");
    expect(await officialPage.evaluate(() => window.opener === null)).toBe(true);
    expect(interceptedOfficialRequests).toBe(1);
    await officialPage.close();
  });
}
