import "server-only";

import type { DetailState } from "./detail-state";
import { proxyCatalogGet } from "./gateway.server";
import { ToolResponseSchema } from "./types";

export async function loadToolDetail(toolId: string): Promise<DetailState> {
  // Reuse the allowlisted server transport. Navigation query stays in the UI;
  // no return URL or client-provided origin is forwarded upstream.
  const response = await proxyCatalogGet(new Request("http://catalog.internal/"), {
    resource: "tool", toolId,
  });
  if (response.status === 404 || response.status === 422) return { status: "not_found" };
  const failure: DetailState = { status: "error", requestId: response.headers.get("x-request-id") };
  if (!response.ok) return failure;
  try {
    const parsed = ToolResponseSchema.safeParse(await response.json());
    return parsed.success ? { status: "ready", data: parsed.data.data } : failure;
  } catch { return failure; }
}
