// Archived 2026-10-18: Figma-prototype mock types (hype/evidence scores, mock articles,
// timeline, chat, mapping queue). Used only by archive/mockData; not part of the live app.

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

