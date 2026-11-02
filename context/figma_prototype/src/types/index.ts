// ────────────────────────────────────────────────
// TYPES - Shared TypeScript Interfaces
// ────────────────────────────────────────────────

// ────────────────────────────────────────────────
// API Response Types
// ────────────────────────────────────────────────

export interface TickerSearchResult {
  ticker: string;
  cik: string;
  sector?: string;
  current_price?: number;
  change_percent?: number;
  price_as_of?: string;
}

export interface TrackedTicker {
  symbol: string;
  name: string;
  sector?: string;
  current_price?: number;
  change_percent?: number;
}

export interface TrackedTicker {
  symbol: string;
  name: string;
  sector?: string;
  current_price?: number;
  change_percent?: number;
  price_as_of?: string;
}

export interface FilingResponse {
  id: string;
  type: string;
  date: string;
  period: string;
  sections: number;
  size: string;
  key: boolean;
}

export interface FilingSummary {
  id: string;
  ticker: string;
  form_type: string;
  period_of_report: string;
  filing_date: string;
  sections: number;
  size: string;
  key: boolean;
}

export interface NewsRow {
  target_ticker: string;
  target_cik: string;
  element_type: string;
  content_body: string;
  normalized_calendar_date: string;
  ingest_date: string;
  source?: string | null;
  url?: string | null;
}

export interface PriceRow {
  target_ticker: string;
  target_cik: string;
  element_type: string;
  content_body: string;
  normalized_calendar_date: string;
  symbol: string;
  timestamp: string;
  current: number;
  change: number;
  percent_change: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
}

export interface FiscalYearEnd {
  target_cik: string;
  fiscal_year_end_date: string;
  source_accession: string;
  extracted_at: string;
}

export interface DashboardStats {
  articles_count: number;          // sec_elements_count + news_articles_count
  sec_elements_count?: number;     // all-time parsed SEC elements
  news_articles_count?: number;    // distinct news articles (by URL)
  sec_filings_count?: number;      // distinct SEC filings (archive + vectorized)
  tickers_count: number;
  vectorized_sec_count: number;
}

export interface TickerResult {
  ticker: string;
  cik: string;
}

export interface SearchResult {
  ticker: string;
  cik: string;
}

export interface PriceRow {
  symbol: string;
  timestamp: string;
  current: number;
  change: number;
  percent_change: number;
  high: number;
  low: number;
  open: number;
  previous_close: number;
}

export interface NewsRow {
  target_ticker: string;
  target_cik: string;
  element_type: string;
  content_body: string;
  normalized_calendar_date: string;
  ingest_date: string;
}

// GET /tickers/{ticker}/timeline (app/models.py TimelineEvent)
export interface TimelineEventResponse {
  normalized_calendar_date: string | null;
  source: "finnhub" | "gnews" | "sec";
  element_type: "quantitative" | "narrative" | "";
  content_body: string;
  current: number | string | null;
  change: number | string | null;
  form_type: string | null;
  item_number: string | null;
  date_precision: string | null;
}

export interface FilingElement {
  id: string;
  target_cik: string;
  accession_number: string;
  form_type: string;
  item_number: string;
  content_type: string;
  raw_text_string: string;
  period_of_report: string;
  filing_date: string;
  date_precision: string;
}

export interface WorkspaceResponse {
  id: number;
  name: string;
  tickers: string[];
  alerts: number;                 // unread alerts for this workspace's tickers
  created_at: string | null;
  description?: string | null;
  alert_on_filings?: boolean;     // keeps a "new SEC filing" alert on for each ticker
}

export interface AlertResponse {
  id: string;
  ticker: string;
  type: string;
  message: string;
  read: boolean;
  severity: string;
  time: string;
}

export interface WorkspaceResponse {
  id: number;
  name: string;
  tickers: string[];
  alerts: number;                 // unread alerts for this workspace's tickers
  created_at: string | null;
  description?: string | null;
  alert_on_filings?: boolean;     // keeps a "new SEC filing" alert on for each ticker
}

export interface AlertResponse {
  id: string;
  ticker: string;
  type: string;
  message: string;
  read: boolean;
  severity: string;
  time: string;
}
export type AlertSubscriptionType = "price_above" | "price_below" | "news" | "filing";

// A subscription the user created (GET /alerts/subscriptions). The last_* fields
// come from the evaluator that runs at the end of each data sync.
export interface AlertSubscription {
  id: number;
  ticker: string;
  alert_type: AlertSubscriptionType;
  threshold: number | null;
  active: boolean;
  created_at: string | null;
  last_observed_label: string | null;
  last_evaluated_at: string | null;
  last_alerted_at: string | null;
}

// GET /alerts/summary: drives the bell dot, the Alerts nav badge and the new-alert pop-up.
export interface AlertSummary {
  unread_count: number;
  newest_unread: AlertResponse | null;
}
