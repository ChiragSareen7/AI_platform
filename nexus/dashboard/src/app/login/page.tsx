"use client";

import { useState } from "react";

export default function LoginPage() {
  const [tenant, setTenant] = useState("00000000-0000-0000-0000-000000000001");
  const [workspace, setWorkspace] = useState("00000000-0000-0000-0000-000000000001");

  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">Operator Login (Dev)</h1>
      <p className="text-slate-400 mt-1">Sets active tenant/workspace in local storage.</p>
      <div className="mt-6 grid gap-3 max-w-xl">
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-2"
          value={tenant}
          onChange={(e) => setTenant(e.target.value)}
          placeholder="tenant uuid"
        />
        <input
          className="bg-slate-900 border border-slate-700 rounded px-3 py-2"
          value={workspace}
          onChange={(e) => setWorkspace(e.target.value)}
          placeholder="workspace uuid"
        />
        <button
          className="bg-cyan-700 hover:bg-cyan-600 rounded px-4 py-2"
          onClick={() => {
            localStorage.setItem("nexus_tenant_id", tenant);
            localStorage.setItem("nexus_workspace_id", workspace);
            alert("Saved active tenant/workspace");
          }}
        >
          Save
        </button>
      </div>
    </main>
  );
}

