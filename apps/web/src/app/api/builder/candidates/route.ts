import { proxyBuilderPost } from "@/lib/catalog/gateway.server";

export const dynamic = "force-dynamic";

export function POST(request: Request): Promise<Response> {
  return proxyBuilderPost(request);
}
