import { createServer, type Server } from "node:http";

import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("server-only", () => ({}));

import { proxyCatalogGet } from "./gateway.server";

const originalBaseUrl = process.env.API_BASE_URL;
const originalTimeout = process.env.CATALOG_API_TIMEOUT_MS;
let server: Server | null = null;

afterEach(async () => {
  if (server !== null) {
    await new Promise<void>((resolve, reject) => {
      server?.close((error) => (error ? reject(error) : resolve()));
    });
    server = null;
  }
  if (originalBaseUrl === undefined) {
    delete process.env.API_BASE_URL;
  } else {
    process.env.API_BASE_URL = originalBaseUrl;
  }
  if (originalTimeout === undefined) {
    delete process.env.CATALOG_API_TIMEOUT_MS;
  } else {
    process.env.CATALOG_API_TIMEOUT_MS = originalTimeout;
  }
});

describe("Catalog gateway failure boundary", () => {
  // Native fetch and AbortSignal.timeout use the platform clock; fake timers do not drive this path.
  it("fails closed before a slow upstream can exceed the configured deadline", async () => {
    server = createServer((_request, response) => {
      setTimeout(() => {
        response.writeHead(200, { "Content-Type": "application/json" });
        response.end('{"data":[],"request_id":"late"}');
      }, 1_500);
    });
    await new Promise<void>((resolve, reject) => {
      server?.listen(0, "127.0.0.1", () => resolve());
      server?.once("error", reject);
    });
    const address = server.address();
    if (address === null || typeof address === "string") {
      throw new Error("Expected a TCP test server.");
    }
    process.env.API_BASE_URL = `http://127.0.0.1:${address.port}`;
    process.env.CATALOG_API_TIMEOUT_MS = "1000";

    const startedAt = performance.now();
    const response = await proxyCatalogGet(
      new Request("http://web.test/api/catalog/categories"),
      { resource: "categories" },
    );
    const elapsedMs = performance.now() - startedAt;
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(elapsedMs).toBeLessThan(1_400);
    expect(body).toMatchObject({ error: { code: "CATALOG_UNAVAILABLE" } });
    expect(response.headers.get("x-request-id")).toBe(body.request_id);
  });

  it("rejects an upstream origin containing credentials without exposing configuration", async () => {
    process.env.API_BASE_URL = "https://user:password@api.example.test";
    process.env.CATALOG_API_TIMEOUT_MS = "10000";

    const response = await proxyCatalogGet(
      new Request("http://web.test/api/catalog/categories"),
      { resource: "categories" },
    );
    const body = await response.json();
    const serialized = JSON.stringify(body);

    expect(response.status).toBe(503);
    expect(body).toMatchObject({ error: { code: "CATALOG_UNAVAILABLE" } });
    expect(serialized).not.toContain("user");
    expect(serialized).not.toContain("password");
    expect(serialized).not.toContain("api.example.test");
  });
});
