import { notFound } from "next/navigation";

const allowed = new Set(["LiveFeed", "PolicyEditor", "AuditLog", "ModelPerf", "Workspaces", "Login"]);

export default function DashboardPage({ params }: { params: { name: string } }) {
  if (!allowed.has(params.name)) return notFound();
  return (
    <main className="p-8">
      <h1 className="text-2xl font-semibold">{params.name}</h1>
      <p className="mt-2 text-slate-400">Scaffold page ready for milestone implementation.</p>
    </main>
  );
}

