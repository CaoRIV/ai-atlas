"use client";

import { useSearchParams } from "next/navigation";
import { ToolDetailContent } from "@/components/tool-detail";

export default function ToolNotFound() {
  const params = useSearchParams();
  return <ToolDetailContent toolId="" initial={{ status: "not_found" }} returnTo={params.get("from") ?? undefined} />;
}
