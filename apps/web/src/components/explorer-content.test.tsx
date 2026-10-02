import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type * as CatalogClientModule from "../lib/catalog/client";
import { getTools } from "../lib/catalog/client";
import type { ToolsResponse } from "../lib/catalog/types";
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
  return { ...original, getTools: vi.fn() };
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

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve;
  });
  return { promise, resolve };
}

function explorerTree() {
  return (
    <LocaleContext.Provider value={{ locale: "vi", setLocale: vi.fn() }}>
      <ExplorerContent />
    </LocaleContext.Provider>
  );
}

beforeEach(() => {
  navigation.paramsText = "";
  navigation.push.mockReset();
  navigation.replace.mockReset();
  vi.mocked(getTools).mockReset();
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

describe("Explorer orchestration", () => {
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
});
