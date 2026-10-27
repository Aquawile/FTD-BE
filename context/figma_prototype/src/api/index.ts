import type {
  TrackedTicker,
  TimelineEventResponse,
  FilingSummary,
  PriceRow,
  NewsRow,
  WorkspaceResponse,
  AlertResponse,
  AlertSubscription,
  AlertSummary,
  AlertSubscriptionType,
  DashboardStats,
} from "../types";
import type { User as FirebaseUser } from "firebase/auth";
import { firebaseAuth } from "../app/firebase";
import { fetchRetry } from "./retry";

export const API_BASE = "/api";

export async function apiRequest(
  path: string,
  firebaseUser: FirebaseUser | null,
  options?: RequestInit,
): Promise<Response> {
  const headers: Record<string, string> = {};
  if (firebaseUser) {
    // Cached token; Firebase refreshes it on its own shortly before it expires.
    // Forcing a refresh here cost a round trip to Google on every API call.
    const token = await firebaseUser.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetchRetry(`${API_BASE}${path}`, { ...options, headers: { ...options?.headers as Record<string, string>, ...headers } });
}

const API_BASE_FALLBACK = "/api";

// Sends the signed-in user's Firebase ID token (cached; Firebase refreshes it before it expires).
async function fetchWithAuth<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const token = firebaseAuth.currentUser ? await firebaseAuth.currentUser.getIdToken() : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const response = await fetchRetry(`${API_BASE_FALLBACK}${endpoint}`, {
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
  // The API returns most recently updated first; every list that shows these wants A-Z.
  const rows = await fetchWithAuth<TrackedTicker[]>(`/tickers/tracked?limit=${limit}`);
  return rows.slice().sort((a, b) => a.symbol.localeCompare(b.symbol));
}

/** One ticker's name, sector and latest price (same source as the dashboard list). */
export async function getTrackedTicker(symbol: string): Promise<TrackedTicker | null> {
  const rows = await fetchWithAuth<TrackedTicker[]>(`/tickers/tracked?symbol=${encodeURIComponent(symbol)}&limit=1`);
  return rows[0] ?? null;
}

/** A quote more than STALE_QUOTE_DAYS older than the reference date is treated as stale
 *  (Finnhub keeps returning an old quote for some symbols). */
export const STALE_QUOTE_DAYS = 7;

/** Newest price_as_of across a list of tickers: the reference for "stale", so weekends
 *  or a late sync don't make every ticker look stale. */
export function newestQuoteDate(rows: { price_as_of?: string | null }[]): string | null {
  return rows.reduce<string | null>((max, r) => (r.price_as_of && (!max || r.price_as_of > max) ? r.price_as_of : max), null);
}

export function isStaleQuote(priceAsOf: string | null | undefined, reference: string | Date | null): boolean {
  if (!priceAsOf || !reference) return false;
  const ref = typeof reference === "string" ? new Date(reference) : reference;
  return ref.getTime() - new Date(priceAsOf).getTime() > STALE_QUOTE_DAYS * 24 * 60 * 60 * 1000;
}

/** Prices are shown with 2 decimals everywhere so the list, header and financials agree. */
export function formatPrice(price: number | string | null | undefined): string {
  if (price == null || price === "") return "—";
  const n = Number(price);
  return Number.isFinite(n) ? n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
}

export async function getTickerNews(ticker: string): Promise<NewsRow[]> {
  return fetchWithAuth<NewsRow[]>(`/tickers/${ticker}/news`);
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
  // Archives the workspace (hidden from the list, kept in the database).
  const res = await apiRequest(`/workspaces/${id}`, firebaseUser, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to archive workspace");
}

export async function fetchUpdateWorkspace(
  id: number,
  change: { name?: string; description?: string; alert_on_filings?: boolean },
  firebaseUser: FirebaseUser | null,
): Promise<WorkspaceResponse> {
  const res = await apiRequest(`/workspaces/${id}`, firebaseUser, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(change),
  });
  return jsonOrThrow(res);
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

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function markAlertsRead(firebaseUser: FirebaseUser | null, alertIds?: number[]): Promise<{ updated: number }> {
  const res = await apiRequest("/alerts/read", firebaseUser, {
    method: "POST", headers: JSON_HEADERS, body: JSON.stringify({ alert_ids: alertIds ?? null }),
  });
  return jsonOrThrow(res);
}

export async function getAlertSummary(firebaseUser: FirebaseUser | null): Promise<AlertSummary> {
  return jsonOrThrow(await apiRequest("/alerts/summary", firebaseUser));
}

export async function getAlertSubscriptions(firebaseUser: FirebaseUser | null): Promise<AlertSubscription[]> {
  return jsonOrThrow(await apiRequest("/alerts/subscriptions", firebaseUser));
}

export async function createAlertSubscription(
  firebaseUser: FirebaseUser | null,
  body: { ticker: string; alert_type: AlertSubscriptionType; threshold?: number | null },
): Promise<AlertSubscription> {
  const res = await apiRequest("/alerts/subscriptions", firebaseUser, {
    method: "POST", headers: JSON_HEADERS, body: JSON.stringify(body),
  });
  return jsonOrThrow(res);
}

export async function updateAlertSubscription(
  firebaseUser: FirebaseUser | null,
  id: number,
  body: { active?: boolean; threshold?: number },
): Promise<AlertSubscription> {
  const res = await apiRequest(`/alerts/subscriptions/${id}`, firebaseUser, {
    method: "PATCH", headers: JSON_HEADERS, body: JSON.stringify(body),
  });
  return jsonOrThrow(res);
}

// ────────────────────────────────────────────────
// Dashboard Endpoints
// ────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchWithAuth<DashboardStats>("/dashboard/stats");
}
