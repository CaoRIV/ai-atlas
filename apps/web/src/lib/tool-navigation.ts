import { buildExplorerHref, parseExplorerState } from "./explorer-state";

export function explorerReturnHref(value?: string | null): string {
  if (!value || (value !== "/explorer" && !value.startsWith("/explorer?"))) return "/explorer";
  return buildExplorerHref(parseExplorerState(new URLSearchParams(value.split("?")[1] ?? "")));
}

export function safeHttps(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}
