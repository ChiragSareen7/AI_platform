import Link from "next/link";

const pages = [
  { label: "Live Feed", href: "/live-feed" },
  { label: "Policy Editor", href: "/policy-editor" },
  { label: "Audit Log", href: "/audit-log" },
  { label: "Model Performance", href: "/model-perf" },
  { label: "Workspaces", href: "/workspaces" },
  { label: "Login", href: "/login" },
];

export default function HomePage() {
  return (
    <main className="p-8">
      <h1 className="text-3xl font-bold">Nexus Operator Dashboard</h1>
      <p className="mt-2 text-slate-400">AI governance and orchestration control plane.</p>
      <ul className="mt-6 grid grid-cols-2 gap-3 max-w-2xl">
        {pages.map((p) => (
          <li key={p.href} className="rounded border border-slate-700 p-3">
            <Link href={p.href} className="text-cyan-300 hover:underline">
              {p.label}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

