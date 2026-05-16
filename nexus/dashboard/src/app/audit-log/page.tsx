"use client";

import { useEffect, useState } from "react";

export default function AuditLogPage() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
    fetch(`${base}/governance/api/v1/query-traces?limit=200`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]));
  }, []);
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Audit Log</h1>
      <p className="text-slate-400 mt-1">Searchable governance trace snapshot.</p>
      <pre className="mt-6 text-xs bg-slate-900 p-4 rounded border border-slate-800 overflow-auto">
        {JSON.stringify(items.slice(0, 50), null, 2)}
      </pre>
    </main>
  );
}

