import { Suspense } from "react";

import { ExplorerContent } from "@/components/explorer-content";

export default function ExplorerPage() {
  return (
    <Suspense fallback={<div aria-busy="true" className="route-loading" />}>
      <ExplorerContent />
    </Suspense>
  );
}
