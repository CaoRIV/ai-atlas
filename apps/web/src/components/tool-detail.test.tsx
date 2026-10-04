import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogClientError, getTool } from "../lib/catalog/client";
import type { ToolDetail } from "../lib/catalog/types";
import { explorerReturnHref } from "../lib/tool-navigation";
import { LocaleContext } from "./locale-context";
import { ToolDetailContent } from "./tool-detail";

vi.mock("../lib/catalog/client", async (original) => ({
  ...await original<typeof import("../lib/catalog/client")>(), getTool: vi.fn(),
}));

const tool: ToolDetail = {
  id: "tool-id", slug: "sample", name: "Sample", description: "Catalog description",
  categories: [], provider: { id: "provider", name: "Provider" }, tags: [], models: [],
  pricing: { model: "unknown", verification_status: "unknown" },
  last_verified_at: "2026-09-30T15:00:00Z", official_url: "https://www.python.org/",
  revision: 1, capabilities: [], warnings: ["fact_unknown:pricing"],
  facts: [
    { key: "api_available", value: false, verification_status: "verified", evidence_ids: ["e1"] },
    { key: "pricing", value: null, verification_status: "unknown", evidence_ids: [] },
    { key: "offline_supported", value: false, verification_status: "unverified", evidence_ids: [] },
  ],
  evidence: [
    { id: "e1", fact_key: "api_available", source_url: "https://docs.python.org/3/", checked_at: "2026-09-30T15:00:00Z", expires_at: "2026-12-29T15:00:00Z" },
    { id: "e2", fact_key: "offline_supported", source_url: "https://docs.python.org/3/", checked_at: "2026-01-01T00:00:00Z", expires_at: "2026-03-01T00:00:00Z" },
  ],
};

function view(initial: Parameters<typeof ToolDetailContent>[0]["initial"], locale: "vi" | "en" = "vi") {
  return <LocaleContext.Provider value={{ locale, setLocale: vi.fn() }}>
    <ToolDetailContent toolId={tool.id} returnTo="/explorer?q=Sample&page=2" initial={initial} />
  </LocaleContext.Provider>;
}

afterEach(() => { cleanup(); vi.clearAllMocks(); });

describe("tool detail", () => {
  it("distinguishes known empty integration conditions from unknown nested values", () => {
    render(view({ status: "ready", data: { ...tool, facts: [{ key: "integration:sample", verification_status: "verified", evidence_ids: [], value: { target_tool_id: null, target_name: "Target", mechanism: null, conditions: [] } }] } }, "en"));
    const integration = screen.getByRole("heading", { name: "integration:sample" }).closest("article")!;
    expect(within(integration).getByText("No recorded conditions")).toBeInTheDocument();
    expect(within(integration).getByText("No data yet")).toBeInTheDocument();
  });
  it("keeps verified false, unknown and unverified values distinct with inline dated evidence", () => {
    render(view({ status: "ready", data: tool }));
    const api = screen.getByRole("heading", { name: "API" }).closest("article")!;
    expect(within(api).getByText("Không hỗ trợ")).toBeInTheDocument();
    expect(within(api).getByText("Đã xác minh")).toBeInTheDocument();
    const stale = screen.getByRole("heading", { name: "Hoạt động offline" }).closest("article")!;
    expect(within(stale).getByText("Cần xác minh lại")).toBeInTheDocument();
    expect(within(stale).getByText("Không — chưa xác minh")).toBeInTheDocument();
    expect(stale.querySelector('time[datetime="2026-01-01T00:00:00Z"]')).not.toBeNull();
    expect(screen.getAllByText("Chưa có dữ liệu").length).toBeGreaterThan(0);
    const official = screen.getByRole("link", { name: /Mở website chính thức/ });
    expect(official).toHaveAttribute("target", "_blank");
    expect(official).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByRole("link", { name: /Quay lại Explorer/ })).toHaveAttribute("href", "/explorer?q=Sample&page=2");
    expect(getTool).not.toHaveBeenCalled();
  });

  it("changes locale without losing detail or return filters and does not invent missing groups", () => {
    const { rerender } = render(view({ status: "ready", data: tool }));
    rerender(view({ status: "ready", data: tool }, "en"));
    expect(screen.getByRole("heading", { name: "Sample" })).toBeInTheDocument();
    expect(screen.getByText("No — unverified")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Back to Explorer/ })).toHaveAttribute("href", "/explorer?q=Sample&page=2");
    expect(screen.queryByRole("button", { name: /Save/i })).not.toBeInTheDocument();
    expect(getTool).not.toHaveBeenCalled();
  });

  it("fails closed on unsafe external links and hostile return paths", () => {
    render(view({ status: "ready", data: { ...tool, official_url: "javascript:alert(1)", evidence: tool.evidence.map(e => ({ ...e, source_url: "http://unsafe.test" })) } }));
    expect(screen.queryByRole("link", { name: /Mở website chính thức/ })).toBeNull();
    expect(document.querySelector('a[href^="javascript:"]')).toBeNull();
    expect(document.querySelector('a[href^="http:"]')).toBeNull();
    for (const path of ["https://evil.com", "//evil.com", "/explorer/../evil", "/explorer?next=https://evil.com"]) {
      expect(explorerReturnHref(path)).toBe("/explorer");
    }
    expect(explorerReturnHref("/explorer?q=hello&api_available=false&page=3")).toBe("/explorer?q=hello&api_available=false&page=3");
  });

  it("retries a sanitized error and recovers real detail", async () => {
    vi.mocked(getTool).mockResolvedValue({ data: tool, request_id: "request" });
    render(view({ status: "error", requestId: "request" }));
    expect(screen.getByRole("alert")).toHaveTextContent("request");
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    await screen.findByRole("heading", { name: "Sample" });
    expect(getTool).toHaveBeenCalledWith(tool.id, expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it("does not expose old data when a retry receives public 404", async () => {
    vi.mocked(getTool).mockRejectedValue(new CatalogClientError({ status: 404, code: "NOT_FOUND", requestId: "request" }));
    render(view({ status: "error", requestId: null }));
    fireEvent.click(screen.getByRole("button", { name: "Thử lại" }));
    await screen.findByRole("heading", { name: "Không tìm thấy công cụ này" });
    expect(screen.queryByText("Catalog description")).toBeNull();
    await waitFor(() => expect(screen.queryByRole("button", { name: "Thử lại" })).toBeNull());
  });
});
