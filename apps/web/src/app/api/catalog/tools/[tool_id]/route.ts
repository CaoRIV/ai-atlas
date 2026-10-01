import { proxyCatalogGet } from "@/lib/catalog/gateway.server";

type RouteContext = {
  params: Promise<{ tool_id: string }>;
};

export const dynamic = "force-dynamic";

export async function GET(request: Request, context: RouteContext): Promise<Response> {
  const { tool_id: toolId } = await context.params;
  return proxyCatalogGet(request, { resource: "tool", toolId });
}
