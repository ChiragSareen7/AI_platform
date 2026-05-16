"use client";

import { useEffect, useState } from "react";

export default function ModelPerfPage() {
  const [metrics, setMetrics] = useState<any>(null);
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
    const tenantId = localStorage.getItem("nexus_tenant_id") || "00000000-0000-0000-0000-000000000001";
    const workspaceId = localStorage.getItem("nexus_workspace_id") || "00000000-0000-0000-0000-000000000001";
    fetch(`${base}/api/v1/metrics?tenant_id=${tenantId}&workspace_id=${workspaceId}`)
      .then((r) => r.json())
      .then((d) => setMetrics(d))
      .catch(() => setMetrics(null));
  }, []);
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Model Performance</h1>
      <pre className="mt-6 text-xs bg-slate-900 p-4 rounded border border-slate-800 overflow-auto">
        {JSON.stringify(metrics, null, 2)}
      </pre>
    </main>
  );
}

