import type {
  TrackedTicker,
  WorkspaceResponse,
  AlertSubscription,
  AlertSummary,
  AlertSubscriptionType,
  DashboardStats,
} from "../types";
import type { User as FirebaseUser } from "firebase/auth";
import { firebaseAuth } from "../app/firebase";
import { fetchRetry } from "./retry";

export const API_BASE = "/api";

// Cached token; Firebase refreshes it on its own shortly before it expires.
// Forcing a refresh here cost a round trip to Google on every API call.
async function bearerHeader(user: FirebaseUser | null): Promise<Record<string, string>> {
  return user ? { Authorization: `Bearer ${await user.getIdToken()}` } : {};
}

// Raw request with an explicit user; the caller reads the Response itself.
export async function apiRequest(
  path: string,
  firebaseUser: FirebaseUser | null,
  options?: RequestInit,
): Promise<Response> {
  const headers = await bearerHeader(firebaseUser);
  return fetchRetry(`${API_BASE}${path}`, { ...options, headers: { ...options?.headers as Record<string, string>, ...headers } });
}

// Same request for whoever is signed in now; returns parsed JSON and throws on a non-OK response.
async function fetchWithAuth<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options?.headers as Record<string, string>) || {}),
    ...(await bearerHeader(firebaseAuth.currentUser)),
  };
  const response = await fetchRetry(`${API_BASE}${endpoint}`, {
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

/**
 * Turn one alert type on or off for a group of tickers (a workspace), using the same
 * per-ticker subscriptions as the Alerts page: existing ones are resumed/paused, missing
 * ones are created when turning on. Returns the user's subscriptions afterwards.
 */
export async function setAlertForTickers(
  firebaseUser: FirebaseUser | null,
  tickers: string[],
  alertType: "news" | "filing",
  on: boolean,
): Promise<AlertSubscription[]> {
  const existing = await getAlertSubscriptions(firebaseUser);
  for (const ticker of tickers) {
    const sub = existing.find(s => s.ticker === ticker && s.alert_type === alertType);
    if (sub && sub.active !== on) await updateAlertSubscription(firebaseUser, sub.id, { active: on });
    else if (!sub && on) await createAlertSubscription(firebaseUser, { ticker, alert_type: alertType });
  }
  return getAlertSubscriptions(firebaseUser);
}

/** True when every ticker has an active subscription of this type. */
export function alertCoversTickers(subs: AlertSubscription[], tickers: string[], alertType: AlertSubscriptionType): boolean {
  return tickers.length > 0 && tickers.every(t => subs.some(s => s.ticker === t && s.alert_type === alertType && s.active));
}

/** The user's saved profile photo (a small JPEG data URL), or null. Kept with the account, not the browser. */
export async function getAvatar(firebaseUser: FirebaseUser | null): Promise<string | null> {
  const body = await jsonOrThrow<{ avatar: string | null }>(await apiRequest("/users/me/avatar", firebaseUser));
  return body.avatar;
}

export async function saveAvatar(firebaseUser: FirebaseUser | null, avatar: string): Promise<void> {
  const res = await apiRequest("/users/me/avatar", firebaseUser, {
    method: "PUT", headers: JSON_HEADERS, body: JSON.stringify({ avatar }),
  });
  if (!res.ok) throw new Error("Couldn't save your photo. Try a smaller image.");
}

export async function deleteAccountRecord(firebaseUser: FirebaseUser | null): Promise<void> {
  const res = await apiRequest("/users/me", firebaseUser, { method: "DELETE" });
  if (!res.ok) throw new Error("Couldn't close your account. Nothing was deleted.");
}

// ────────────────────────────────────────────────
// Dashboard Endpoints
// ────────────────────────────────────────────────

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchWithAuth<DashboardStats>("/dashboard/stats");
}

// The API checks the address has an account and asks Firebase to email the reset link.
// Resolves true if sent, false if there is no account; throws if the request itself fails.
export async function requestPasswordReset(email: string): Promise<boolean> {
  const res = await fetchRetry(`${API_BASE}/auth/password-reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: email.trim() }),
  });
  if (!res.ok) throw new Error("Couldn't send the reset email.");
  return (await res.json()).sent === true;
}
