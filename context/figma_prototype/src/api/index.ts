import type {
  TrackedTicker,
  NewsArticleResponse,
  TimelineEventResponse,
  FilingSummary,
  PriceRow,
  WorkspaceResponse,
  AlertResponse,
  DashboardStats,
} from "../types";
import { FirebaseUser } from "firebase/auth";

export const API_BASE = "/api";

export async function apiRequest(
  path: string,
  firebaseUser: FirebaseUser | null,
  options?: RequestInit,
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (firebaseUser) {
    const token = await firebaseUser.getIdToken(true);
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_BASE}${path}`, { ...options, headers: { ...options?.headers as Record<string, string>, ...headers } });
}

const API_BASE_FALLBACK = "/api";

async function fetchWithAuth<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem("auth_token");
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options?.headers || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetch(`${API_BASE_FALLBACK}${endpoint}`, {
    ...options,
    headers,
    signal: options?.signal,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: response.statusText }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }
  return response.json();
}

// ────────────────────────────────────────────────
// Ticker Endpoints
// ────────────────────────────────────────────────

export async function searchTickers(
  query: string,
  options?: { limit?: number; sector?: string; sortBy?: string }
): Promise<TrackedTicker[]> {
  const params = new URLSearchParams({
    q: query,
    limit: (options?.limit ?? 20).toString(),
  });
  if (options?.sector && options.sector !== "all") {
    params.set("sector", options.sector);
  }
  if (options?.sortBy) {
    params.set("sort_by", options.sortBy);
  }
  return fetchWithAuth<TrackedTicker[]>(`/tickers/search?${params.toString()}`);
}

export async function getTrackedTickers(limit = 500): Promise<TrackedTicker[]> {
  return fetchWithAuth<TrackedTicker[]>(`/tickers/tracked?limit=${limit}`);
}

export async function getTickerNews(ticker: string): Promise<NewsArticleResponse[]> {
  return fetchWithAuth<NewsArticleResponse[]>(`/tickers/${ticker}/news`);
}

export async function getTickerTimeline(ticker: string): Promise<TimelineEventResponse[]> {
  return fetchWithAuth<TimelineEventResponse[]>(`/tickers/${ticker}/timeline`);
}

export async function getTickerFilings(ticker: string): Promise<FilingSummary[]> {
  return fetchWithAuth<FilingSummary[]>(`/tickers/${ticker}/filings`);
}

export async function getTickerPrices(ticker: string): Promise<PriceRow[]> {
  return fetchWithAuth<PriceRow[]>(`/tickers/${ticker}/prices`);
}

// ────────────────────────────────────────────────
// Workspace Endpoints (Firebase auth)
// ────────────────────────────────────────────────

export async function fetchWorkspaces(firebaseUser: FirebaseUser | null): Promise<WorkspaceResponse[]> {
  const res = await apiRequest("/workspaces", firebaseUser);
  if (!res.ok) throw new Error("Failed to fetch workspaces");
  return res.json();
}

export async function fetchCreateWorkspace(
  name: string,
  tickerSymbols: string[],
  firebaseUser: FirebaseUser | null,
): Promise<WorkspaceResponse> {
  const res = await apiRequest("/workspaces", firebaseUser, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, ticker_symbols: tickerSymbols }),
  });
  if (!res.ok) throw new Error("Failed to create workspace");
  return res.json();
}

export async function fetchDeleteWorkspace(
  id: string | number,
  firebaseUser: FirebaseUser | null,
): Promise<void> {
  const res = await apiRequest(`/workspaces/${id}`, firebaseUser, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete workspace");
}

export async function fetchWorkspaceTickers(
  id: string | number,
  firebaseUser: FirebaseUser | null,
): Promise<string[]> {
  const res = await apiRequest(`/workspaces/${id}/tickers`, firebaseUser);
  if (!res.ok) throw new Error("Failed to fetch workspace tickers");
  return res.json();
}

export async function fetchAddTickerToWorkspace(
  id: string | number,
  tickerSymbol: string,
  firebaseUser: FirebaseUser | null,
): Promise<void> {
  const res = await apiRequest(`/workspaces/${id}/tickers`, firebaseUser, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker_symbol: tickerSymbol }),
  });
  if (!res.ok) throw new Error("Failed to add ticker");
}

export async function fetchRemoveTickerFromWorkspace(
  id: string | number,
  tickerSymbol: string,
  firebaseUser: FirebaseUser | null,
): Promise<void> {
  const res = await apiRequest(`/workspaces/${id}/tickers/${tickerSymbol}`, firebaseUser, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to remove ticker");
}

// ────────────────────────────────────────────────
// Workspace Endpoints (legacy - localStorage auth)
// ────────────────────────────────────────────────

export async function getWorkspaces(): Promise<WorkspaceResponse[]> {
  return fetchWithAuth<WorkspaceResponse[]>("/workspaces");
}

export async function getWorkspace(id: string): Promise<WorkspaceResponse> {
  return fetchWithAuth<WorkspaceResponse>(`/workspaces/${id}`);
}

export async function createWorkspace(name: string, tickerSymbols: string[]): Promise<WorkspaceResponse> {
  return fetchWithAuth<WorkspaceResponse>("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name, ticker_symbols: tickerSymbols }),
  });
}

export async function updateWorkspace(id: string, data: { name?: string; tickerSymbols?: string[] }): Promise<WorkspaceResponse> {
  return fetchWithAuth<WorkspaceResponse>(`/workspaces/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data.tickerSymbols ? { ...data, ticker_symbols: data.tickerSymbols } : data),
  });
}

export async function deleteWorkspace(id: string): Promise<void> {
  await fetchWithAuth<void>(`/workspaces/${id}`, { method: "DELETE" });
}

// ────────────────────────────────────────────────
// Alert Endpoints
// ────────────────────────────────────────────────

export async function getAlerts(limit = 10): Promise<AlertResponse[]> {
  return fetchWithAuth<AlertResponse[]>(`/alerts?limit=${limit}`);
}

// ────────────────────────────────────────────────
// Dashboard Endpoints
// ────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchWithAuth<DashboardStats>("/dashboard/stats");
}

// ────────────────────────────────────────────────
// Auth Endpoints
// ────────────────────────────────────────────────

export async function login(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  return fetchWithAuth<{ access_token: string; token_type: string }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  return fetchWithAuth<{ access_token: string; token_type: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  localStorage.removeItem("auth_token");
  window.location.href = "/login";
}