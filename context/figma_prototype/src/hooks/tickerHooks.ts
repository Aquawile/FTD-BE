import { useState, useEffect } from "react";
import { getTrackedTickers } from "../api";
import { TrackedTicker } from "../types";

// The tracked-ticker list (same source as the dashboard; sorted by symbol).
export function useTrackedTickers(limit = 500) {
  const [tickers, setTickers] = useState<TrackedTicker[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setLoading(true);
    getTrackedTickers(limit)
      .then(setTickers)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [limit]);

  return { tickers, loading, error, refetch: () => getTrackedTickers(limit).then(setTickers).catch(() => {}) };
}
