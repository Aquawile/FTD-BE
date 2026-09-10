import { useState, useEffect } from "react";

export * from "./tickerHooks";

export function useWorkspace(id: string) {
  const [workspace, setWorkspace] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/workspaces/${id}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setWorkspace(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [id]);

  return { workspace, loading, error, refetch: () => fetch(`/api/workspaces/${id}`).then(r => r.ok ? r.json() : Promise.reject()).then(setWorkspace).catch(() => setError(true)) };
}

export function useWorkspaces() {
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/workspaces")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setWorkspaces(data); })
      .catch(() => { if (!cancelled) setError(true); setLoading(false); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  return { workspaces, loading, error, refetch: () => fetch("/api/workspaces").then(r => r.ok ? r.json() : Promise.reject()).then(setWorkspaces).catch(() => setError(true)) };
}

export function useCreateWorkspace() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const createWorkspace = async (name: string, tickerSymbols: string[]) => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, tickerSymbols }),
      });
      if (!res.ok) throw new Error("Failed to create workspace");
      return await res.json();
    } catch (err) {
      setError(true);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createWorkspace, loading, error };
}

export function useDeleteWorkspace() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const deleteWorkspace = async (id: string) => {
    setLoading(true);
    setError(false);
    try {
      const res = await fetch(`/api/workspaces/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete workspace");
    } catch (err) {
      setError(true);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { deleteWorkspace, loading, error };
}

// ────────────────────────────────────────────────
// Workspace Tickers Hooks
// ────────────────────────────────────────────────

export function useWorkspaceTickers(workspaceId: string) {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/workspaces/${workspaceId}/tickers`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setTickers(data); })
      .catch(() => setError(true))
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [workspaceId]);

  return { tickers, loading, error, refetch: () => fetch(`/api/workspaces/${workspaceId}/tickers`).then(r => r.ok ? r.json() : Promise.reject()).then(setTickers).catch(() => setError(true)) };
}

export function useAddTickerToWorkspace() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const addTicker = async (workspaceId: string, tickerSymbol: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/tickers`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tickerSymbol }),
      });
      if (!res.ok) throw new Error("Failed to add ticker");
      return await res.json();
    } catch (err) {
      setError(true);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { addTicker, loading, error };
}

export function useRemoveTickerFromWorkspace() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const removeTicker = async (workspaceId: string, tickerSymbol: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/workspaces/${workspaceId}/tickers/${tickerSymbol}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to remove ticker");
    } catch (err) {
      setError(true);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { removeTicker, loading, error };
}

// ────────────────────────────────────────────────
// Alert Hooks
// ────────────────────────────────────────────────

export function useAlerts(limit = 10) {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`/api/alerts?limit=${limit}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setAlerts(data); })
      .catch(() => { if (!cancelled) setError(true); setLoading(false); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [limit]);

  return { alerts, loading, error, refetch: () => fetch(`/api/alerts?limit=${limit}`).then(r => r.ok ? r.json() : Promise.reject()).then(setAlerts).catch(() => setError(true)) };
}

export function useMarkAlertRead() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const markRead = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/alerts/${id}/read`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to mark alert as read");
    } catch (err) {
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { markRead, loading, error };
}

export function useMarkAllAlertsRead() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const markAllRead = async () => {
    setLoading(true);
    try {
      await fetch("/api/alerts/read-all", { method: "POST" });
    } catch (err) {
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { markAllRead, loading, error };
}

// ────────────────────────────────────────────────
// Dashboard Stats Hook
// ────────────────────────────────────────────────

export function useDashboardStats() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/dashboard/stats")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setStats(data); })
      .catch(() => { if (!cancelled) setError(true); setLoading(false); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  return { stats, loading, error, refetch: () => fetch("/api/dashboard/stats").then(r => r.ok ? r.json() : Promise.reject()).then(setStats).catch(() => setError(true)) };
}

// ────────────────────────────────────────────────
// Auth Hooks
// ────────────────────────────────────────────────

export function useAuth() {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      fetch("/api/auth/me", {
        headers: { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }
      })
        .then(r => r.ok ? r.json() : Promise.reject())
        .then(data => setUser(data))
        .catch(() => setError(true))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error("Invalid credentials");
    const data = await res.json();
    localStorage.setItem("auth_token", data.access_token);
    const userRes = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${data.access_token}` }
    });
    const user = await userRes.json();
    setUser(user);
    return data;
  };

  const logout = () => {
    localStorage.removeItem("auth_token");
    setUser(null);
  };

  return { user, loading, error, login, logout, isAuthenticated: !!user };
}