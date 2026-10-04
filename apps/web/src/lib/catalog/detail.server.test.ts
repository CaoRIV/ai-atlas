import { describe, expect, it, vi } from "vitest";
import { proxyCatalogGet } from "./gateway.server";
import { loadToolDetail } from "./detail.server";

vi.mock("server-only", () => ({}));
vi.mock("./gateway.server", () => ({ proxyCatalogGet: vi.fn() }));

describe("server detail boundary", () => {
  it("maps absent/archived and invalid IDs to public not_found", async () => {
    for (const status of [404, 422]) {
      vi.mocked(proxyCatalogGet).mockResolvedValue(Response.json({ private: "hidden" }, { status }));
      expect(await loadToolDetail("id")).toEqual({ status: "not_found" });
    }
  });
  it("sanitizes upstream failure and malformed success without exposing content", async () => {
    for (const status of [200, 503]) {
      vi.mocked(proxyCatalogGet).mockResolvedValue(Response.json({ private: "hidden" }, { status, headers: { "x-request-id": "request" } }));
      expect(await loadToolDetail("id")).toEqual({ status: "error", requestId: "request" });
    }
  });
});
