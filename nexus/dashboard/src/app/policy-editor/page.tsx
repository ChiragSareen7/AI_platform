"use client";

import { useEffect, useState } from "react";

type Rule = {
  id: string;
  metric: string;
  operator: string;
  threshold: number;
  action: string;
  priority: number;
  description: string;
};

export default function PolicyEditorPage() {
  const [rules, setRules] = useState<Rule[]>([]);

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
    const workspaceId = localStorage.getItem("nexus_workspace_id") || "00000000-0000-0000-0000-000000000001";
    fetch(`${base}/governance/api/v1/policy-rules?workspace_id=${workspaceId}`)
      .then((r) => r.json())
      .then((d) => setRules(Array.isArray(d) ? d : []))
      .catch(() => setRules([]));
  }, []);

  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Policy Editor</h1>
      <p className="text-slate-400 mt-1">Current governance rules for active workspace.</p>
      <ul className="mt-6 space-y-2">
        {rules.map((r) => (
          <li key={r.id} className="rounded border border-slate-800 p-3">
            <div className="font-medium">{r.description}</div>
            <div className="text-slate-400 text-sm mt-1">
              {r.metric} {r.operator} {r.threshold} =&gt; {r.action} (priority {r.priority})
            </div>
          </li>
        ))}
      </ul>
    </main>
  );
}

