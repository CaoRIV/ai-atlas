import { afterEach, describe, expect, it, vi } from "vitest";

import { CatalogClientError, getTool, getTools } from "./client";

const requestId = "50000000-0000-4000-8000-000000000001";
const toolId = "10000000-0000-4000-8000-000000000001";

function response(body: unknown, status = 200, headers?: HeadersInit): Response {
  return Response.json(body, { status, headers });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Catalog client boundary", () => {
  it("accepts a tool detail containing explicit unknown facts and evidence metadata", async () => {
    const body = {
      data: {
        id: toolId,
        slug: "tool-one",
        name: "Tool One",
        description: "A catalog tool.",
        categories: [
          {
            id: "20000000-0000-4000-8000-000000000001",
            slug: "research-learning",
            name: "Research & Learning",
          },
        ],
        pricing: { model: "unknown", verification_status: "unknown" },
        last_verified_at: "2026-09-30T15:00:00Z",
        official_url: "https://tool.example.org/",
        provider: null,
        tags: ["research"],
        models: [],
        capabilities: [
          {
            key: "web_research",
            name: "Web Research",
            evidence_ids: ["30000000-0000-4000-8000-000000000001"],
          },
        ],
        facts: [
          {
            key: "pricing",
            value: null,
            verification_status: "unknown",
            evidence_ids: [],
          },
        ],
        evidence: [
          {
            id: "30000000-0000-4000-8000-000000000001",
            fact_key: "capability:web_research",
            source_url: "https://tool.example.org/docs",
            checked_at: "2026-09-30T15:00:00Z",
            expires_at: "2026-12-29T15:00:00Z",
          },
        ],
        revision: 1,
        warnings: ["fact_unknown:pricing"],
      },
      request_id: requestId,
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(body)));

    await expect(getTool(toolId)).resolves.toEqual(body);
  });

  it("rejects a successful response that violates the Catalog contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(
          { data: [], request_id: requestId },
          200,
          { "X-Request-ID": requestId },
        ),
      ),
    );

    await expect(getTools()).rejects.toMatchObject({
      status: 502,
      code: "INVALID_CATALOG_RESPONSE",
      requestId,
    } satisfies Partial<CatalogClientError>);
  });

  it("preserves backend error metadata needed for localized recovery", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response(
          {
            error: {
              code: "VALIDATION_ERROR",
              message: "Dữ liệu đầu vào không hợp lệ.",
              details: [{ field: "page", reason: "greater_than_equal" }],
            },
            request_id: requestId,
          },
          422,
          { "Retry-After": "7", "X-Request-ID": requestId },
        ),
      ),
    );

    await expect(getTools("page=0")).rejects.toMatchObject({
      status: 422,
      code: "VALIDATION_ERROR",
      requestId,
      retryAfter: "7",
      details: [{ field: "page", reason: "greater_than_equal" }],
    } satisfies Partial<CatalogClientError>);
  });

  it("distinguishes an aborted request from Catalog unavailability", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")));

    await expect(getTools("", { signal: controller.signal })).rejects.toMatchObject({
      status: 0,
      code: "REQUEST_ABORTED",
      requestId: null,
    } satisfies Partial<CatalogClientError>);
  });
});
