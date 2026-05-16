export async function apiGet<T>(path: string): Promise<T> {
  const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
  const res = await fetch(`${base}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

