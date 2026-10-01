import "server-only";

import type { CatalogErrorResponse } from "./types";

const defaultTimeoutMs = 10_000;
const minimumTimeoutMs = 1_000;
const maximumTimeoutMs = 30_000;
const forwardedResponseHeaders = [
  "content-type",
  "x-request-id",
  "retry-after",
  "allow",
  "www-authenticate",
] as const;

type CatalogTarget =
  | { resource: "categories" }
  | { resource: "tools" }
  | { resource: "tool"; toolId: string };

type CatalogServerConfig = {
  baseUrl: URL;
  timeoutMs: number;
};

class CatalogConfigurationError extends Error {}

function readCatalogServerConfig(): CatalogServerConfig {
  const rawBaseUrl = process.env.API_BASE_URL;
  if (!rawBaseUrl) {
    throw new CatalogConfigurationError("missing_api_base_url");
  }

  let baseUrl: URL;
  try {
    baseUrl = new URL(rawBaseUrl);
  } catch {
    throw new CatalogConfigurationError("invalid_api_base_url");
  }
  if (
    !["http:", "https:"].includes(baseUrl.protocol) ||
    baseUrl.username !== "" ||
    baseUrl.password !== "" ||
    baseUrl.search !== "" ||
    baseUrl.hash !== "" ||
    !["", "/"].includes(baseUrl.pathname)
  ) {
    throw new CatalogConfigurationError("invalid_api_base_url");
  }

  const rawTimeout = process.env.CATALOG_API_TIMEOUT_MS;
  const timeoutMs = rawTimeout === undefined ? defaultTimeoutMs : Number(rawTimeout);
  if (
    !Number.isInteger(timeoutMs) ||
    timeoutMs < minimumTimeoutMs ||
    timeoutMs > maximumTimeoutMs
  ) {
    throw new CatalogConfigurationError("invalid_catalog_api_timeout");
  }

  return { baseUrl, timeoutMs };
}

function targetPath(target: CatalogTarget): string {
  if (target.resource === "categories") {
    return "/api/v1/categories";
  }
  if (target.resource === "tools") {
    return "/api/v1/tools";
  }
  return `/api/v1/tools/${encodeURIComponent(target.toolId)}`;
}

function unavailableResponse(requestId: string): Response {
  const body: CatalogErrorResponse = {
    error: {
      code: "CATALOG_UNAVAILABLE",
      message: "Dịch vụ catalog hiện không khả dụng.",
      details: [],
    },
    request_id: requestId,
  };
  return Response.json(body, {
    status: 503,
    headers: {
      "Cache-Control": "no-store",
      "X-Request-ID": requestId,
    },
  });
}

export async function proxyCatalogGet(request: Request, target: CatalogTarget): Promise<Response> {
  const requestId = crypto.randomUUID();
  try {
    const config = readCatalogServerConfig();
    const sourceUrl = new URL(request.url);
    const upstreamUrl = new URL(targetPath(target), config.baseUrl);
    upstreamUrl.search = sourceUrl.search;

    const response = await fetch(upstreamUrl, {
      method: "GET",
      headers: {
        Accept: "application/json",
        "X-Request-ID": requestId,
      },
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(config.timeoutMs)]),
    });

    const headers = new Headers({ "Cache-Control": "no-store" });
    for (const name of forwardedResponseHeaders) {
      const value = response.headers.get(name);
      if (value !== null) {
        headers.set(name, value);
      }
    }
    if (!headers.has("x-request-id")) {
      headers.set("x-request-id", requestId);
    }

    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  } catch {
    return unavailableResponse(requestId);
  }
}
