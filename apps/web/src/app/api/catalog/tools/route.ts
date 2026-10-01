import { proxyCatalogGet } from "@/lib/catalog/gateway.server";

export const dynamic = "force-dynamic";

export function GET(request: Request): Promise<Response> {
  return proxyCatalogGet(request, { resource: "tools" });
}
