import { notFound } from "next/navigation";
import { ToolDetailContent } from "@/components/tool-detail";
import { loadToolDetail } from "@/lib/catalog/detail.server";
import { explorerReturnHref } from "@/lib/tool-navigation";

export default async function ToolPage({ params, searchParams }: {
  params: Promise<{ tool_id: string }>;
  searchParams: Promise<{ from?: string | string[] }>;
}) {
  const { tool_id } = await params;
  const { from } = await searchParams;
  const initial = await loadToolDetail(tool_id);
  if (initial.status === "not_found") notFound();
  return <ToolDetailContent key={tool_id} toolId={tool_id} initial={initial}
    returnTo={explorerReturnHref(typeof from === "string" ? from : null)} />;
}
