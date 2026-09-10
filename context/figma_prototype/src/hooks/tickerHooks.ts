// ────────────────────────────────────────────────
// Ticker Dashboard Hooks
// ────────────────────────────────────────────────

import { useState, useEffect, useCallback } from "react";
import { TrackedTicker } from "../types";

export function useTickerSearch(query: string, options?: { limit?: number; sector?: string; sortBy?: string }) {
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const search = useCallback(async () => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(false);
    try {
      const params = new URLSearchParams({
        q: query,
        limit: (options?.limit ?? 20).toString(),
      });
      if (options?.sector && options.sector !== "all") params.set("sector", options.sector);
      params.set("sort_by", options?.sortBy || "ticker");
      const res = await fetch(`/api/tickers/search?${params.toString()}`, {
        headers: { "Content-Type": "application/json" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResults(Array.isArray(data) ? data : []);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [query, options?.sector, options?.sortBy, options?.limit]);

  useEffect(() => {
    const timeout = setTimeout(() => search(), 300);
    return () => clearTimeout(timeout);
  }, [query, search]);

  return { results, loading, error, search };
}

export function useTickerDashboard(ticker: string) {
  const [articles, setArticles] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [filings, setFilings] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;

    const loadData = async () => {
      try {
        const [news, timeline, filings, evidence, tracked] = await Promise.all([
          fetch(`/api/tickers/${ticker}/news`).then(r => r.ok ? r.json() : []).catch(() => []),
          fetch(`/api/tickers/${ticker}/timeline`).then(r => r.ok ? r.json() : []).catch(() => []),
          fetch(`/api/tickers/${ticker}/filings`).then(r => r.ok ? r.json() : []).catch(() => []),
          fetch(`/api/tickers/${ticker}/evidence`).then(r => r.ok ? r.json() : []).catch(() => []),
          fetch(`/api/tickers/tracked`).then(r => r.ok ? r.json() : []).catch(() => []),
        ]);

        if (!cancelled) {
          setArticles(news);
          setTimeline(timeline);
          setFilings(filings);
          setEvidence(evidence);
        }
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadData();
    return () => { /* cancelled = true */ };
  }, [ticker]);
}

export function useTickerNews(ticker: string) {
  const [articles, setArticles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    fetch(`/api/tickers/${ticker}/news`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setArticles(data); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [ticker]);

  return { articles, loading, error };
}

export function useTickerTimeline(ticker: string) {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    fetch(`/api/tickers/${ticker}/timeline`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setTimeline(data); })
      .catch(() => { setError(true); })
      .finally(() => setLoading(false));
    return () => { /* cancelled = true */ };
  }, [ticker]);

  return { timeline, loading, error };
}

export function useTickerFilings(ticker: string) {
  const [filings, setFilings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/tickers/${ticker}/filings`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setFilings(data); })
      .catch(() => { setError(true); })
      .finally(() => { setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [ticker]);

  return { filings, loading, error };
}

export function useTickerEvidence(ticker: string) {
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/tickers/${ticker}/evidence`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setEvidence(data); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [ticker]);

  return { evidence, loading, error };
}

export function useTrackedTickers(limit = 500) {
  const [tickers, setTickers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`/api/tickers/tracked?limit=${limit}`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) setTickers(data); })
      .catch(() => setError(true))
      .finally(() => { setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [limit]);

  return { tickers, loading, error, refetch: () => fetch(`/api/tickers/tracked?limit=500`).then(r => r.ok ? r.json() : Promise.reject()).then(setTickers).catch(() => {}) };
}