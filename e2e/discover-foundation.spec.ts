import { expect, test } from "@playwright/test";

test("serves the curated Discover baseline through the real stack", async ({ page, request }) => {
  const response = await request.get("/api/catalog/tools?sort=name&page=1&page_size=20");
  expect(response.status()).toBe(200);
  const body = (await response.json()) as {
    data: Array<{ id: string; name: string }>;
    pagination: { page: number; page_size: number; total: number };
  };
  expect(body.pagination).toEqual({ page: 1, page_size: 20, total: 15 });
  expect(body.data.map((tool) => tool.name)).toEqual([
    "Adobe Firefly",
    "ChatGPT",
    "Claude",
    "Cursor",
    "ElevenLabs",
    "Gemini",
    "GitHub Copilot",
    "Langflow",
    "Midjourney",
    "n8n",
    "NotebookLM",
    "Otter.ai",
    "Perplexity",
    "Runway",
    "Zapier",
  ]);

  const navigation = await page.goto("/explorer");
  expect(navigation?.status()).toBe(200);
  await expect(page.getByRole("main")).toBeVisible();
  const detailLinks = page.locator('main a[href^="/tools/"]');
  await expect(detailLinks).toHaveCount(body.pagination.total);
  await expect(detailLinks.first()).toHaveAttribute(
    "href",
    new RegExp(`^/tools/${body.data[0].id}(?:\\?|$)`),
  );
});
