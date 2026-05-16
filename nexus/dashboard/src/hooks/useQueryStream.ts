import { useEffect } from "react";

export function useQueryStream(url: string) {
  useEffect(() => {
    const ev = new EventSource(url);
    return () => ev.close();
  }, [url]);
}

