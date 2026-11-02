import { useState, useEffect } from "react";
import type { User as FirebaseUser } from "firebase/auth";
import { apiRequest } from "../api";

export * from "./tickerHooks";

export function useAlerts(limit = 10, firebaseUser: FirebaseUser | null = null) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchAlerts = async () => {
    const res = await apiRequest(`/alerts?limit=${limit}`, firebaseUser);
    if (!res.ok) throw new Error("Failed to fetch alerts");
    return res.json();
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchAlerts()
      .then(data => { if (!cancelled) setAlerts(data); })
      .catch(() => { if (!cancelled) setError(true); setLoading(false); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [limit, firebaseUser]);

  return { alerts, loading, error, refetch: () => fetchAlerts().then(setAlerts).catch(() => setError(true)) };
}

