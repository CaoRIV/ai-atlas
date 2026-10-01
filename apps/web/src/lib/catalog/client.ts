import type { ZodType } from "zod";

import {
  CatalogErrorResponseSchema,
  CategoriesResponseSchema,
  ToolResponseSchema,
  ToolsResponseSchema,
  type CatalogErrorDetail,
  type CategoriesResponse,
  type ToolResponse,
  type ToolsResponse,
} from "./types";

type CatalogRequestOptions = {
  signal?: AbortSignal;
};

type ErrorMetadata = {
  status: number;
  code: string;
  requestId: string | null;
  details?: CatalogErrorDetail[];
  retryAfter?: string | null;
};

export class CatalogClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: CatalogErrorDetail[];
  readonly retryAfter: string | null;

  constructor(metadata: ErrorMetadata) {
    super(metadata.code);
    this.name = "CatalogClientError";
    this.status = metadata.status;
    this.code = metadata.code;
    this.requestId = metadata.requestId;
    this.details = metadata.details ?? [];
    this.retryAfter = metadata.retryAfter ?? null;
  }
}

async function requestCatalog<T>(
  path: string,
  schema: ZodType<T>,
  options: CatalogRequestOptions = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      signal: options.signal,
    });
  } catch {
    throw new CatalogClientError({
      status: 0,
      code: options.signal?.aborted ? "REQUEST_ABORTED" : "CATALOG_UNAVAILABLE",
      requestId: null,
    });
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // The typed boundary below converts an invalid body into a stable client error.
  }

  if (!response.ok) {
    const parsedError = CatalogErrorResponseSchema.safeParse(body);
    if (parsedError.success) {
      throw new CatalogClientError({
        status: response.status,
        code: parsedError.data.error.code,
        requestId: parsedError.data.request_id,
        details: parsedError.data.error.details,
        retryAfter: response.headers.get("retry-after"),
      });
    }
    throw new CatalogClientError({
      status: response.status,
      code: "CATALOG_REQUEST_FAILED",
      requestId: response.headers.get("x-request-id"),
      retryAfter: response.headers.get("retry-after"),
    });
  }

  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    throw new CatalogClientError({
      status: 502,
      code: "INVALID_CATALOG_RESPONSE",
      requestId: response.headers.get("x-request-id"),
    });
  }
  return parsed.data;
}

export function getCategories(options?: CatalogRequestOptions): Promise<CategoriesResponse> {
  return requestCatalog("/api/catalog/categories", CategoriesResponseSchema, options);
}

export function getTools(
  query: URLSearchParams | string = "",
  options?: CatalogRequestOptions,
): Promise<ToolsResponse> {
  const serialized = typeof query === "string" ? query.replace(/^\?/, "") : query.toString();
  const suffix = serialized ? `?${serialized}` : "";
  return requestCatalog(`/api/catalog/tools${suffix}`, ToolsResponseSchema, options);
}

export function getTool(toolId: string, options?: CatalogRequestOptions): Promise<ToolResponse> {
  return requestCatalog(`/api/catalog/tools/${encodeURIComponent(toolId)}`, ToolResponseSchema, options);
}
