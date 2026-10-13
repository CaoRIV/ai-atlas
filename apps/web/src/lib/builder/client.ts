import { CatalogErrorResponseSchema, type CatalogErrorDetail } from "../catalog/types";
import {
  BuilderLiteRequestSchema,
  BuilderLiteResponseSchema,
  type BuilderLiteRequest,
  type BuilderLiteResponse,
} from "./types";

type ErrorMetadata = {
  status: number;
  code: string;
  requestId: string | null;
  details?: CatalogErrorDetail[];
};

export class BuilderClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly details: CatalogErrorDetail[];

  constructor(metadata: ErrorMetadata) {
    super(metadata.code);
    this.name = "BuilderClientError";
    this.status = metadata.status;
    this.code = metadata.code;
    this.requestId = metadata.requestId;
    this.details = metadata.details ?? [];
  }
}

export async function buildCandidates(
  request: BuilderLiteRequest,
  options: { signal?: AbortSignal } = {},
): Promise<BuilderLiteResponse> {
  const validatedRequest = BuilderLiteRequestSchema.parse(request);
  let response: Response;
  try {
    response = await fetch("/api/builder/candidates", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(validatedRequest),
      signal: options.signal,
    });
  } catch {
    throw new BuilderClientError({
      status: 0,
      code: options.signal?.aborted ? "REQUEST_ABORTED" : "BUILDER_UNAVAILABLE",
      requestId: null,
    });
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // The schema boundary below turns invalid upstream data into a stable error.
  }

  if (!response.ok) {
    const parsedError = CatalogErrorResponseSchema.safeParse(body);
    if (parsedError.success) {
      throw new BuilderClientError({
        status: response.status,
        code: parsedError.data.error.code,
        requestId: parsedError.data.request_id,
        details: parsedError.data.error.details,
      });
    }
    throw new BuilderClientError({
      status: response.status,
      code: "BUILDER_REQUEST_FAILED",
      requestId: response.headers.get("x-request-id"),
    });
  }

  const parsed = BuilderLiteResponseSchema.safeParse(body);
  if (!parsed.success) {
    throw new BuilderClientError({
      status: 502,
      code: "INVALID_BUILDER_RESPONSE",
      requestId: response.headers.get("x-request-id"),
    });
  }
  return parsed.data;
}
