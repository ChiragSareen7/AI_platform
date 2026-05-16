import { useQuery } from "@tanstack/react-query";

export function useThresholds() {
  return useQuery({
    queryKey: ["thresholds"],
    queryFn: async () => {
      const base = process.env.NEXT_PUBLIC_NEXUS_API || "http://localhost:8090";
      const res = await fetch(`${base}/governance/api/v1/thresholds`);
      if (!res.ok) throw new Error("Failed to fetch thresholds");
      return res.json();
    },
  });
}

