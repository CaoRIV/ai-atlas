import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as CatalogClientModule from "../lib/catalog/client";
import { CatalogClientError, getCategories, getTools } from "../lib/catalog/client";
import type { CategoriesResponse, ToolsResponse } from "../lib/catalog/types";
import { HomeContent } from "./home-content";
import { LocaleContext } from "./locale-context";

const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("../lib/catalog/client", async (importOriginal) => {
  const original = await importOriginal<typeof CatalogClientModule>();
  return {
    ...original,
    getCategories: vi.fn(),
    getTools: vi.fn(),
  };
});

const requestId = "60000000-0000-4000-8000-000000000001";
const categoriesResponse: CategoriesResponse = {
  data: [
    { id: "category-1", slug: "coding-development", name: "Lập trình" },
    { id: "category-2", slug: "research", name: "Nghiên cứu" },
    { id: "category-3", slug: "productivity", name: "Năng suất" },
  ],
  request_id: requestId,
};
const toolsResponse: ToolsResponse = {
  data: [
    {
      id: "tool-alpha",
      slug: "alpha",
      name: "Alpha",
      description: "Trợ lý phát triển phần mềm có mô tả đủ dài để kiểm tra dữ liệu thật từ summary.",
      categories: categoriesResponse.data,
      pricing: { model: "freemium", verification_status: "verified" },
      last_verified_at: "2026-09-30T00:00:00Z",
    },
    {
      id: "tool-beta",
      slug: "beta",
      name: "Beta",
      description: "Công cụ nghiên cứu với trạng thái giá chưa được xác minh.",
      categories: [categoriesResponse.data[1]],
      pricing: { model: "paid", verification_status: "unverified" },
      last_verified_at: null,
    },
  ],
  pagination: { page: 1, page_size: 6, total: 2 },
  request_id: requestId,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

function renderHome() {
  return render(
    <LocaleContext.Provider value={{ locale: "vi", setLocale: vi.fn() }}>
      <HomeContent />
    </LocaleContext.Provider>,
  );
}

beforeEach(() => {
  pushMock.mockReset();
  vi.mocked(getCategories).mockReset();
  vi.mocked(getTools).mockReset();
});

afterEach(cleanup);

describe("Home discovery", () => {
  it("loads real Catalog summaries and builds searchable Explorer URLs", async () => {
    const categories = deferred<CategoriesResponse>();
    const tools = deferred<ToolsResponse>();
    vi.mocked(getCategories).mockReturnValue(categories.promise);
    vi.mocked(getTools).mockReturnValue(tools.promise);

    renderHome();

    expect(screen.getByText("Đang tải danh mục…")).toBeInTheDocument();
    expect(screen.getByText("Đang tải công cụ…")).toBeInTheDocument();

    await act(async () => {
      categories.resolve(categoriesResponse);
      tools.resolve(toolsResponse);
      await Promise.all([categories.promise, tools.promise]);
    });

    expect(screen.getByRole("link", { name: "Lập trình" })).toHaveAttribute(
      "href",
      "/explorer?category=coding-development",
    );
    const alphaCard = screen.getByText("Alpha").closest("article");
    expect(alphaCard).not.toBeNull();
    expect(within(alphaCard!).getByText("Có gói miễn phí")).toBeInTheDocument();
    expect(within(alphaCard!).getByText("+1")).toBeInTheDocument();
    expect(within(alphaCard!).queryByText("Năng suất")).not.toBeInTheDocument();
    expect(within(alphaCard!).getByRole("link", { name: "Xem chi tiết Alpha" })).toHaveAttribute(
      "href",
      "/tools/tool-alpha",
    );
    expect(screen.getByText("Cần xác minh giá")).toBeInTheDocument();

    const query = vi.mocked(getTools).mock.calls[0]?.[0];
    expect(query?.toString()).toBe("page=1&page_size=6&sort=name");

    fireEvent.change(screen.getByLabelText("Bạn đang tìm công cụ nào?"), {
      target: { value: "  mô hình tiếng Việt  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Tìm công cụ" }));

    expect(pushMock).toHaveBeenCalledWith(
      "/explorer?q=m%C3%B4+h%C3%ACnh+ti%E1%BA%BFng+Vi%E1%BB%87t",
    );
  });

  it("renders explicit empty states without invented counts or tools", async () => {
    vi.mocked(getCategories).mockResolvedValue({ data: [], request_id: requestId });
    vi.mocked(getTools).mockResolvedValue({
      data: [],
      pagination: { page: 1, page_size: 6, total: 0 },
      request_id: requestId,
    });

    renderHome();

    expect(await screen.findByText("Chưa có danh mục công khai.")).toBeInTheDocument();
    expect(screen.getByText("Chưa có công cụ công khai trong thư viện.")).toBeInTheDocument();
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
  });

  it("shows a sanitized request ID and recovers the failed tool section", async () => {
    vi.mocked(getCategories).mockResolvedValue(categoriesResponse);
    vi.mocked(getTools)
      .mockRejectedValueOnce(
        new CatalogClientError({
          status: 503,
          code: "CATALOG_UNAVAILABLE",
          requestId,
        }),
      )
      .mockResolvedValueOnce(toolsResponse);

    renderHome();

    expect(await screen.findByText("Chưa thể tải công cụ lúc này.")).toBeInTheDocument();
    expect(screen.getByText(requestId)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));

    await waitFor(() => expect(screen.getByText("Alpha")).toBeInTheDocument());
    expect(getTools).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Chưa thể tải công cụ lúc này.")).not.toBeInTheDocument();
  });
});
