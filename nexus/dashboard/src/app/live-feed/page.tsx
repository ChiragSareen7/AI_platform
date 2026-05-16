"use client";

import { useEffect, useState } from "react";

type Trace = {
  id: string;
  raw_query: string;
  model_selected: string;
  policy_decision: string;
  score_overall: number;
  latency_ms: number;
};

export default function LiveFeedPage() {
  const [items, setItems] = useState<Trace[]>([]);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
    const tenantId = localStorage.getItem("nexus_tenant_id") || "00000000-0000-0000-0000-000000000001";
    const workspaceId = localStorage.getItem("nexus_workspace_id") || "00000000-0000-0000-0000-000000000001";
    fetch(`${base}/governance/api/v1/query-traces?limit=100`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]));

    const es = new EventSource(`${base}/api/v1/stream?x_tenant_id=${tenantId}&x_workspace_id=${workspaceId}`);
    es.onmessage = () => {
      fetch(`${base}/governance/api/v1/query-traces?limit=100`)
        .then((r) => r.json())
        .then((d) => setItems(d.items || []))
        .catch(() => {});
    };
    return () => es.close();
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Live Feed</h1>
      <p className="text-slate-400 mt-1">Latest query traces with governance decisions.</p>
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-400">
            <tr>
              <th className="py-2">Query</th>
              <th>Model</th>
              <th>Decision</th>
              <th>Score</th>
              <th>Latency</th>
            </tr>
          </thead>
          <tbody>
            {items.map((x) => (
              <tr key={x.id} className="border-t border-slate-800">
                <td className="py-2">{x.raw_query}</td>
                <td>{x.model_selected}</td>
                <td>{x.policy_decision}</td>
                <td>{x.score_overall}</td>
                <td>{x.latency_ms} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}

