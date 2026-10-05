import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as CatalogClientModule from "../lib/catalog/client";
import { CatalogClientError, getCategories, getTools } from "../lib/catalog/client";
import type { CategoriesResponse, ToolsResponse } from "../lib/catalog/types";
import { ExplorerContent } from "./explorer-content";
import { LocaleContext } from "./locale-context";

const navigation = vi.hoisted(() => ({
  paramsText: "",
  push: vi.fn(),
  replace: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  usePathname: () => "/explorer",
  useRouter: () => ({ push: navigation.push, replace: navigation.replace }),
  useSearchParams: () => new URLSearchParams(navigation.paramsText),
}));

vi.mock("../lib/catalog/client", async (importOriginal) => {
  const original = await importOriginal<typeof CatalogClientModule>();
  return { ...original, getCategories: vi.fn(), getTools: vi.fn() };
});

function toolsResponse(name: string, page = 1, total = 1): ToolsResponse {
  return {
    data: [
      {
        id: `tool-${name.toLowerCase()}`,
        slug: name.toLowerCase(),
        name,
        description: `${name} catalog description`,
        categories: [],
        pricing: { model: "unknown", verification_status: "unknown" },
        last_verified_at: null,
      },
    ],
    pagination: { page, page_size: 20, total },
    request_id: "60000000-0000-4000-8000-000000000004",
  };
}

function categoriesResponse(): CategoriesResponse {
  return {
    data: [
      { id: "category-coding", slug: "coding-development", name: "Coding & Development" },
      { id: "category-research", slug: "research-learning", name: "Research & Learning" },
    ],
    request_id: "60000000-0000-4000-8000-000000000005",
  };
}

function emptyToolsResponse(): ToolsResponse {
  return {
    data: [],
    pagination: { page: 1, page_size: 20, total: 0 },
    request_id: "60000000-0000-4000-8000-000000000006",
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

function explorerTree(locale: "vi" | "en" = "vi") {
  return (
    <LocaleContext.Provider value={{ locale, setLocale: vi.fn() }}>
      <ExplorerContent />
    </LocaleContext.Provider>
  );
}

beforeEach(() => {
  navigation.paramsText = "";
  navigation.push.mockReset();
  navigation.replace.mockReset();
  vi.mocked(getCategories).mockReset();
  vi.mocked(getCategories).mockResolvedValue(categoriesResponse());
  vi.mocked(getTools).mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Explorer orchestration", () => {
  it("keeps URL, applied filters, pagination and an open drawer draft when locale changes", async () => {
    navigation.paramsText = "q=chat&category=coding-development&sort=updated&page=2";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha", 2, 25));
    const view = render(explorerTree());
    await screen.findByText("Alpha");
    fireEvent.click(screen.getByRole("button", { name: "Bộ lọc (1)" }));
    const dialog = await screen.findByRole("dialog", { name: "Bộ lọc" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Research & Learning" }));
    fireEvent.change(within(dialog).getByLabelText("Khả dụng API"), { target: { value: "false" } });

    view.rerender(explorerTree("en"));
    const translated = screen.getByRole("dialog", { name: "Filters" });
    expect(within(translated).getByRole("checkbox", { name: "Research & Learning" })).toBeChecked();
    expect(within(translated).getByRole("checkbox", { name: "Coding & Development" })).toBeChecked();
    expect(within(translated).getByLabelText("API available")).toHaveValue("false");
    expect(navigation.paramsText).toBe("q=chat&category=coding-development&sort=updated&page=2");
    expect(navigation.push).not.toHaveBeenCalled();
    expect(getTools).toHaveBeenCalledTimes(1);
    fireEvent.click(within(translated).getByRole("button", { name: "Apply" }));
    expect(navigation.push).toHaveBeenCalledWith("/explorer?q=chat&category=coding-development%2Cresearch-learning&api_available=false&sort=updated");
  });

  it("translates errors and request IDs without discarding the query or refetching", async () => {
    navigation.paramsText = "q=chat&sort=updated&page=2";
    vi.mocked(getTools).mockRejectedValue(new CatalogClientError({ status: 503, code: "CATALOG_UNAVAILABLE", requestId: "retained-request" }));
    const view = render(explorerTree());
    await screen.findByRole("alert");
    view.rerender(explorerTree("en"));
    expect(screen.getByRole("alert")).toHaveTextContent("Results are unavailable right now.");
    expect(screen.getByRole("alert")).toHaveTextContent("retained-request");
    expect(screen.getByLabelText("Search by name or task")).toHaveValue("chat");
    expect(navigation.push).not.toHaveBeenCalled();
    expect(getTools).toHaveBeenCalledTimes(1);
  });
  it("loads URL-derived filters and resets page for explicit sort and pagination actions", async () => {
    navigation.paramsText =
      "q=chat&category=chatting-assistants,ai-agents&platform=web&pricing_model=free&api_available=false&open_source=true&sort=updated&page=2";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha", 2, 25));

    render(explorerTree());

    expect(await screen.findByText("Alpha")).toBeInTheDocument();
    expect(screen.getByLabelText("Tìm theo tên hoặc tác vụ")).toHaveValue("chat");
    expect(screen.getByLabelText("Sắp xếp")).toHaveValue("updated");
    expect(screen.getByRole("option", { name: "Liên quan nhất" })).toBeInTheDocument();
    expect(vi.mocked(getTools).mock.calls[0]?.[0]?.toString()).toBe(
      "q=chat&category=chatting-assistants%2Cai-agents&platform=web&pricing_model=free&api_available=false&open_source=true&sort=updated&page=2&page_size=20",
    );

    fireEvent.click(screen.getByRole("button", { name: "Trang trước" }));
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/explorer?q=chat&category=chatting-assistants%2Cai-agents&platform=web&pricing_model=free&api_available=false&open_source=true&sort=updated",
    );

    fireEvent.change(screen.getByLabelText("Sắp xếp"), { target: { value: "name" } });
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/explorer?q=chat&category=chatting-assistants%2Cai-agents&platform=web&pricing_model=free&api_available=false&open_source=true&sort=name",
    );
  });

  it("waits 300ms after composition and lets Enter commit immediately without a late duplicate", async () => {
    vi.useFakeTimers();
    navigation.paramsText = "q=old&sort=relevance&page=3";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha", 3));

    render(explorerTree());
    const input = screen.getByLabelText("Tìm theo tên hoặc tác vụ");

    fireEvent.compositionStart(input);
    fireEvent.change(input, { target: { value: "mô" } });
    await act(() => vi.advanceTimersByTimeAsync(500));
    expect(navigation.replace).not.toHaveBeenCalled();

    fireEvent.compositionEnd(input);
    await act(() => vi.advanceTimersByTimeAsync(299));
    expect(navigation.replace).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(1));
    expect(navigation.replace).toHaveBeenCalledWith("/explorer?q=m%C3%B4&sort=relevance");

    navigation.replace.mockClear();
    fireEvent.change(input, { target: { value: "new query" } });
    fireEvent.click(screen.getByRole("button", { name: "Tìm kiếm" }));
    expect(navigation.push).toHaveBeenCalledWith("/explorer?q=new+query&sort=relevance");
    await act(() => vi.advanceTimersByTimeAsync(300));
    expect(navigation.replace).not.toHaveBeenCalled();
  });

  it("restores URL state and prevents an aborted older response from replacing newer results", async () => {
    const oldRequest = deferred<ToolsResponse>();
    const newRequest = deferred<ToolsResponse>();
    navigation.paramsText = "q=old";
    vi.mocked(getTools)
      .mockReturnValueOnce(oldRequest.promise)
      .mockReturnValueOnce(newRequest.promise);

    const view = render(explorerTree());
    const oldSignal = vi.mocked(getTools).mock.calls[0]?.[1]?.signal;
    expect(screen.getByLabelText("Tìm theo tên hoặc tác vụ")).toHaveValue("old");

    navigation.paramsText = "q=new&page=2";
    view.rerender(explorerTree());

    expect(oldSignal?.aborted).toBe(true);
    expect(screen.getByLabelText("Tìm theo tên hoặc tác vụ")).toHaveValue("new");
    await act(async () => {
      newRequest.resolve(toolsResponse("New", 2));
      await newRequest.promise;
    });
    expect(screen.getByText("New")).toBeInTheDocument();

    await act(async () => {
      oldRequest.resolve(toolsResponse("Old"));
      await oldRequest.promise;
    });
    await waitFor(() => expect(screen.queryByText("Old")).not.toBeInTheDocument());
    expect(screen.getByText("New")).toBeInTheDocument();
  });

  it("applies desktop filters immediately with category OR and removes All boolean params", async () => {
    navigation.paramsText = "q=chat&category=coding-development&api_available=false&page=3";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha", 3));

    const view = render(explorerTree());
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
    await screen.findByText("Research & Learning");

    fireEvent.click(screen.getByRole("checkbox", { name: "Research & Learning" }));
    expect(navigation.push).toHaveBeenLastCalledWith(
      "/explorer?q=chat&category=coding-development%2Cresearch-learning&api_available=false",
    );

    navigation.paramsText = "q=chat&api_available=false&page=3";
    view.rerender(explorerTree());
    fireEvent.change(screen.getByLabelText("Khả dụng API"), { target: { value: "" } });
    expect(navigation.push).toHaveBeenLastCalledWith("/explorer?q=chat");
  });

  it("discards mobile drafts on Escape and Cancel, then applies once and restores trigger focus", async () => {
    navigation.paramsText = "category=coding-development&platform=web";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha"));
    render(explorerTree());
    await screen.findByText("Alpha");
    const trigger = screen.getByRole("button", { name: "Bộ lọc (2)" });

    fireEvent.click(trigger);
    let dialog = await screen.findByRole("dialog", { name: "Bộ lọc" });
    fireEvent.click(within(dialog).getByRole("checkbox", { name: "Research & Learning" }));
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Bộ lọc" })).not.toBeInTheDocument());
    expect(navigation.push).not.toHaveBeenCalled();
    expect(trigger).toHaveFocus();

    fireEvent.click(trigger);
    dialog = await screen.findByRole("dialog", { name: "Bộ lọc" });
    expect(within(dialog).getByRole("checkbox", { name: "Research & Learning" })).not.toBeChecked();
    fireEvent.change(within(dialog).getByLabelText("Khả dụng API"), { target: { value: "true" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Xóa lựa chọn" }));
    expect(within(dialog).getByRole("checkbox", { name: "Coding & Development" })).not.toBeChecked();
    expect(within(dialog).getByLabelText("Nền tảng")).toHaveValue("");
    expect(within(dialog).getByLabelText("Khả dụng API")).toHaveValue("");
    fireEvent.click(within(dialog).getByRole("button", { name: "Hủy" }));
    expect(navigation.push).not.toHaveBeenCalled();

    fireEvent.click(trigger);
    dialog = await screen.findByRole("dialog", { name: "Bộ lọc" });
    expect(within(dialog).getByLabelText("Khả dụng API")).toHaveValue("");
    fireEvent.change(within(dialog).getByLabelText("Khả dụng API"), { target: { value: "true" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Áp dụng" }));
    expect(navigation.push).toHaveBeenCalledTimes(1);
    expect(navigation.push).toHaveBeenCalledWith(
      "/explorer?category=coding-development&platform=web&api_available=true",
    );
    await waitFor(() => expect(trigger).toHaveFocus());
  });

  it("removes applied chips by keyboard-accessible buttons while preserving other state", async () => {
    navigation.paramsText =
      "q=chat&category=coding-development,research-learning&api_available=false&page=4";
    vi.mocked(getTools).mockResolvedValue(toolsResponse("Alpha", 4));
    render(explorerTree());
    await screen.findByText("Coding & Development");

    fireEvent.click(
      screen.getByRole("button", { name: "Bỏ bộ lọc: Danh mục: Coding & Development" }),
    );
    expect(navigation.push).toHaveBeenCalledWith(
      "/explorer?q=chat&category=research-learning&api_available=false",
    );
  });

  it("keeps the old grid aria-busy while a refreshed result is pending", async () => {
    const refreshed = deferred<ToolsResponse>();
    navigation.paramsText = "q=old";
    vi.mocked(getTools)
      .mockResolvedValueOnce(toolsResponse("Old"))
      .mockReturnValueOnce(refreshed.promise);

    const view = render(explorerTree());
    expect(await screen.findByText("Old")).toBeInTheDocument();

    navigation.paramsText = "q=new";
    view.rerender(explorerTree());
    expect(screen.getByText("Old")).toBeInTheDocument();
    const refreshStatus = screen.getByRole("status", { name: "" });
    expect(refreshStatus).toHaveTextContent("Đang cập nhật kết quả");
    expect(refreshStatus.parentElement).toHaveAttribute("aria-busy", "true");

    await act(async () => {
      refreshed.resolve(toolsResponse("New"));
      await refreshed.promise;
    });
    await waitFor(() => expect(screen.queryByText("Old")).not.toBeInTheDocument());
    expect(screen.getByText("New")).toBeInTheDocument();
    expect(screen.queryByText(/Đang cập nhật kết quả/)).not.toBeInTheDocument();
  });

  it("offers a full query reset for 422 and preserves the URL for retryable HTTP errors", async () => {
    navigation.paramsText = "q=chat&category=not-a-category&sort=updated";
    vi.mocked(getTools).mockRejectedValueOnce(
      new CatalogClientError({
        code: "VALIDATION_ERROR",
        requestId: "60000000-0000-4000-8000-000000000422",
        status: 422,
      }),
    );
    const view = render(explorerTree());

    expect(await screen.findByText("Query hoặc bộ lọc trong URL không hợp lệ.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Đặt lại tìm kiếm và bộ lọc" }));
    expect(navigation.push).toHaveBeenCalledWith("/explorer");

    navigation.push.mockReset();
    navigation.paramsText = "q=chat&sort=relevance";
    vi.mocked(getTools)
      .mockRejectedValueOnce(
        new CatalogClientError({
          code: "CATALOG_UNAVAILABLE",
          requestId: "60000000-0000-4000-8000-000000000503",
          status: 503,
        }),
      )
      .mockResolvedValueOnce(toolsResponse("Recovered"));
    view.rerender(explorerTree());

    expect(await screen.findByText("Chưa thể tải kết quả lúc này.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    expect(await screen.findByText("Recovered")).toBeInTheDocument();
    expect(navigation.push).not.toHaveBeenCalled();
    expect(vi.mocked(getTools).mock.calls.at(-1)?.[0]?.toString()).toBe(
      "q=chat&sort=relevance&page=1&page_size=20",
    );
  });

  it("clears search and filters from the empty state without changing a valid sort", async () => {
    navigation.paramsText = "q=missing&category=coding-development&api_available=true&sort=updated";
    vi.mocked(getTools).mockResolvedValue(emptyToolsResponse());
    render(explorerTree());

    expect(await screen.findByText("Không có công cụ phù hợp với tìm kiếm và bộ lọc hiện tại.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Xóa tìm kiếm và bộ lọc" }));
    expect(navigation.push).toHaveBeenCalledWith("/explorer?sort=updated");
  });
});
