// ────────────────────────────────────────────────
// TYPES - Shared TypeScript Interfaces
// ────────────────────────────────────────────────

export interface Ticker {
  symbol: string;
  name: string;
  hype: number;
  evidence: number;
  sector: string;
  change: number;
  price: number;
  current_price?: number;
  change_percent?: number;
  price_as_of?: string;
  sector?: string;
  cik?: string;
}

export interface NewsArticle {
  id: number;
  ticker: string;
  headline: string;
  source: string;
  time: string;
  hype: number;
  evidence: number;
  summary: string;
  claims: string[];
  evidenceLinks: string[];
  flagged: boolean;
}

export interface TimelineEvent {
  date: string;
  type: "filing" | "narrative" | "news" | "social" | "earnings";
  title: string;
  description: string;
  score_delta: number;
  hype: number;
  evidence: number;
}

export interface Workspace {
  id: string;
  name: string;
  tickers: string[];
  created: string;
  alerts: number;
}

export interface MappingQueueItem {
  id: string;
  article: string;
  mapped: string;
  suggested: string;
  source: string;
  confidence: number;
  reporter: string;
  time: string;
  type: string;
}

export interface ChatMessage {
  role: "user" | "ai";
  text: string;
  time: string;
  sources?: string[];
}

export interface Alert {
  id: string;
  ticker: string;
  type: "narrative_shift" | "filing" | "narrative_shift" | "hype_spike" | "hype_spike";
  message: string;
  time: string;
  read: boolean;
  severity: "high" | "medium" | "low";
}

export interface Ticker {
  symbol: string;
  name: string;
  hype: number;
  evidence: number;
  sector: string;
  change: number;
  price: number;
  current_price?: number;
  change_percent?: number;
  price_as_of?: string;
  sector?: string;
  cik?: string;
  hype_score?: number;
  evidence_score?: number;
}

export interface NewsArticle {
  id: number;
  ticker: string;
  headline: string;
  source: string;
  time: string;
  hype: number;
  evidence: number;
  summary: string;
  claims: string[];
  evidenceLinks: string[];
  flagged: boolean;
}

export interface TimelineEvent {
  date: string;
  type: "filing" | "narrative" | "news" | "social" | "earnings";
  title: string;
  description: string;
  score_delta: number;
  hype: number;
  evidence: number;
}

export interface Workspace {
  id: string;
  name: string;
  tickers: string[];
  created: string;
  alerts: number;
}

export interface MappingQueueItem {
  id: string;
  article: string;
  mapped: string;
  suggested: string;
  source: string;
  confidence: number;
  reporter: string;
  time: string;
  type: string;
}

export interface ChatMessage {
  role: "user" | "ai";
  text: string;
  time: string;
  sources?: string[];
}

export interface Alert {
  id: string;
  ticker: string;
  type: "narrative_shift" | "filing" | "hype_spike";
  message: string;
  time: string;
  read: boolean;
  severity: "high" | "medium" | "low";
}

export interface Workspace {
  id: string;
  name: string;
  tickers: string[];
  created: string;
  alerts: number;
}

export interface MappingQueueItem {
  id: string;
  article: string;
  mapped: string;
  suggested: string;
  source: string;
  confidence: number;
  reporter: string;
  time: string;
  type: string;
}

export interface ChatMessage {
  role: "user" | "ai";
  text: string;
  time: string;
  sources?: string[];
}

export interface Alert {
  id: string;
  ticker: string;
  type: "narrative_shift" | "filing" | "hype_spike";
  message: string;
  time: string;
  read: boolean;
  severity: "high" | "medium" | "low";
}

// ────────────────────────────────────────────────
// API Response Types
// ────────────────────────────────────────────────

export interface TickerSearchResult {
  ticker: string;
  cik: string;
  sector?: string;
  current_price?: number;
  evidence_score?: number;
  hype_score?: number;
  change_percent?: number;
  price_as_of?: string;
}

export interface TrackedTicker {
  symbol: string;
  name: string;
  sector?: string;
  current_price?: number;
  evidence_score?: number;
  hype_score?: number;
  change_percent?: number;
}

export interface TrackedTicker {
  symbol: string;
  name: string;
  sector?: string;
  current_price?: number;
  evidence_score?: number;
  hype_score?: number;
  change_percent?: number;
  price_as_of?: string;
}

export interface NewsArticleResponse {
  id: number;
  ticker: string;
  headline: string;
  source: string;
  time: string;
  hype: number;
  evidence: number;
  summary: string;
  claims: string[];
  evidenceLinks: string[];
  flagged: boolean;
}

export interface TimelineEventResponse {
  date: string;
  type: "filing" | "narrative" | "news" | "social" | "earnings";
  title: string;
  description: string;
  score_delta: number;
  hype: number;
  evidence: number;
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
  articles_count: number;          // news_articles_count + sec_filings_count
  news_articles_count?: number;    // distinct news articles (by URL)
  sec_filings_count?: number;      // distinct SEC filings (archive + vectorized)
  tickers_count: number;
  alerts_count: number;
  evidence_score: number | null;
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

export interface TimelineEventResponse {
  date: string;
  type: string;
  title: string;
  description: string;
  score_delta: number;
  hype: number;
  evidence: number;
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
  alerts: number;
  created_at: string | null;
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
  alerts: number;
  created_at: string | null;
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
