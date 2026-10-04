import type { ToolDetail } from "./types";

export type DetailState =
  | { status: "ready"; data: ToolDetail }
  | { status: "error"; requestId: string | null }
  | { status: "not_found" }
  | { status: "loading" };
