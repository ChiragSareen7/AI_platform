"use client";

import { useEffect, useState } from "react";

export default function WorkspacesPage() {
  const [data, setData] = useState<any>({});
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
    Promise.all([
      fetch(`${base}/governance/api/v1/tenants`).then((r) => r.json()),
      fetch(`${base}/governance/api/v1/workspaces`).then((r) => r.json()),
    ])
      .then(([tenants, workspaces]) => setData({ tenants, workspaces }))
      .catch(() => setData({ tenants: [], workspaces: [] }));
  }, []);
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Workspaces</h1>
      <pre className="mt-6 text-xs bg-slate-900 p-4 rounded border border-slate-800 overflow-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </main>
  );
}

