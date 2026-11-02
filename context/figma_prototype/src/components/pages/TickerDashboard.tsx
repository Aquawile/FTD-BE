import { useState, useEffect } from "react";
import type { User as FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Modal, cn } from "../ui";
import PriceTimeline from "../PriceTimeline";
import TickerNewsFeed from "../TickerNewsFeed";
import { Bell, Briefcase, ExternalLink, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { apiRequest, fetchAddTickerToWorkspace, fetchWorkspaces, formatPrice, getTrackedTicker, isStaleQuote } from "../../api";
import { TrackedTicker, WorkspaceResponse } from "../../types";

interface PriceRow {
  normalized_calendar_date: string | null;
  current: number | null;
  change: number | null;
  percent_change: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  previous_close: number | null;
}

interface NewsRow {
  target_ticker: string;
  normalized_calendar_date: string | null;
  ingest_date: string | null;
  content_body: string;
  source: string | null;
  url: string | null;
}

interface FilingSummary {
  target_ticker: string;
  target_cik: string;
  form_type: string;
  accession_number: string;
  filing_date: string | null;
  period_of_report?: string | null;
  element_count: number;
  url: string | null;
}

function TickerDashboard({ navigate, ticker, firebaseUser, onSetAlert }: { navigate: (p: Page) => void; ticker: string; firebaseUser: FirebaseUser | null; onSetAlert: (ticker: string) => void }) {
  const [tab, setTab] = useState("overview");
  const [tickerData, setTickerData] = useState<TrackedTicker | null>(null);
  const [prices, setPrices] = useState<PriceRow[]>([]);
  const [news, setNews] = useState<NewsRow[]>([]);
  const [filings, setFilings] = useState<FilingSummary[]>([]);
  const [loading, setLoading] = useState(true);       // header (name + latest price)
  const [pickWorkspace, setPickWorkspace] = useState(false);
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[] | null>(null);
  const [wsMessage, setWsMessage] = useState<string | null>(null);

  const openWorkspacePicker = async () => {
    setPickWorkspace(true); setWsMessage(null); setWorkspaces(null);
    try { setWorkspaces(await fetchWorkspaces(firebaseUser)); } catch { setWorkspaces([]); setWsMessage("Couldn't load your workspaces."); }
  };

  const addToWorkspace = async (ws: WorkspaceResponse) => {
    if (ws.tickers.includes(ticker)) { setWsMessage(`${ticker} is already in ${ws.name}.`); return; }
    try {
      await fetchAddTickerToWorkspace(ws.id, ticker, firebaseUser);
      setWorkspaces(prev => (prev || []).map(w => (w.id === ws.id ? { ...w, tickers: [...w.tickers, ticker] } : w)));
      setWsMessage(`Added ${ticker} to ${ws.name}.`);
    } catch {
      setWsMessage(`Couldn't add ${ticker} to ${ws.name}.`);
    }
  };
  const [detailsLoading, setDetailsLoading] = useState(true);
  const tabs = ["overview", "news"];

  // Each section renders as soon as its own request returns, instead of waiting
  // for the slowest one. The header needs only this ticker, not all 494.
  useEffect(() => {
    let cancelled = false;
    setTickerData(null); setPrices([]); setNews([]); setFilings([]);
    setLoading(true); setDetailsLoading(true);
    const end = new Date().toISOString().split("T")[0];
    const start = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
    const authed = <T,>(path: string, fallback: T): Promise<T> =>
      firebaseUser ? apiRequest(path, firebaseUser).then(r => (r.ok ? r.json() : fallback)).catch(() => fallback) : Promise.resolve(fallback);

    getTrackedTicker(ticker)
      .then(row => { if (!cancelled) setTickerData(row); })
      .catch(() => undefined)
      .finally(() => { if (!cancelled) setLoading(false); });

    const details = [
      authed<PriceRow[]>(`/tickers/${ticker}/prices?start=${start}&end=${end}`, []).then(r => { if (!cancelled) setPrices(r || []); }),
      authed<NewsRow[]>(`/tickers/${ticker}/news?start=2000-01-01&end=${end}&limit=5`, []).then(r => { if (!cancelled) setNews(r || []); }),
      authed<FilingSummary[]>(`/tickers/${ticker}/filings`, []).then(r => { if (!cancelled) setFilings((r || []).slice(0, 10)); }),
    ];
    Promise.all(details).finally(() => { if (!cancelled) setDetailsLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, firebaseUser]);

  const t = tickerData || {
    symbol: ticker,
    name: ticker,
    sector: "",
    current_price: null,
    change_percent: null,
  };

  const getFinancialFromPrices = () => {
    if (!prices || prices.length === 0) return null;
    const latest = prices[prices.length - 1];
    return {
      currentPrice: latest.current ?? null,
      previousClose: latest.previous_close ?? null,
      open: latest.open ?? null,
      high: latest.high ?? null,
      low: latest.low ?? null,
      dailyChange: latest.percent_change != null ? parseFloat(String(latest.percent_change)) : null,
    };
  };

  const financials = getFinancialFromPrices();

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-card border-b border-border px-6 py-5">
        <div className="flex items-start justify-between gap-4 max-w-7xl mx-auto">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center shrink-0">
              <span className="font-mono font-bold text-lg text-foreground">{t.symbol.slice(0, 2)}</span>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold font-mono text-foreground">{t.symbol}</h1>
              </div>
              <div className="text-muted-foreground text-sm">{t.name}</div>
              {loading ? (
                <div className="flex items-center gap-4 mt-2" aria-label="Loading price">
                  <div className="h-6 w-24 bg-secondary rounded animate-pulse" />
                  <div className="h-4 w-14 bg-secondary rounded animate-pulse" />
                </div>
              ) : (
                <div className="flex items-center gap-4 mt-2">
                  <span className="font-mono font-bold text-xl text-foreground">${formatPrice(t.current_price)}</span>
                  {t.change_percent != null && (
                    <span className={cn("flex items-center gap-1 text-sm", t.change_percent > 0 ? "text-emerald-400" : "text-red-400")}>
                      {t.change_percent > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                      {t.change_percent > 0 ? "+" : ""}{Number(t.change_percent).toFixed(2)}%
                    </span>
                  )}
                  {tickerData?.price_as_of && (
                    isStaleQuote(tickerData.price_as_of, new Date()) ? (
                      <span className="text-xs text-amber-400" title="Finnhub has not returned a newer quote for this symbol">
                        last quote {tickerData.price_as_of.slice(0, 10)}
                      </span>
                    ) : (
                      <span className="text-xs text-muted-foreground">as of {tickerData.price_as_of.slice(0, 10)}</span>
                    )
                  )}
                </div>
              )}
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3">
              <Btn variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => onSetAlert(ticker)}>Set Alert</Btn>
              <Btn variant="secondary" size="sm" icon={<Briefcase size={12} />} onClick={openWorkspacePicker}>Add to Workspace</Btn>
            </div>
          </div>
        </div>
        {/* Tabs */}
        <div className="flex gap-0 mt-5 max-w-7xl mx-auto border-b border-transparent -mb-5">
          {tabs.map(tab_ => (
            <button
              key={tab_}
              onClick={() => { setTab(tab_); }}
              className={cn(
                "px-4 py-2 text-sm border-b-2 transition-all cursor-pointer capitalize",
                tab === tab_ ? "border-primary text-primary font-medium" : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab_}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 max-w-7xl mx-auto w-full">
         {tab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main col */}
            <div className="lg:col-span-2 space-y-5">
              {/* Price timeline - REAL DATA (pandas-built 365-day series from staging_finnhub) */}
              <PriceTimeline ticker={ticker} firebaseUser={firebaseUser} />

              {/* Recent news - REAL DATA */}
              <div>
                 <div className="space-y-3">
                   {news.slice(0, 5).map((a, i) => {
                    const sourceLabel = a.source === "gnews" ? "Google News" : a.source === "finnhub" ? "Finnhub" : a.source === "sec" ? "SEC" : a.source || "News";
                    const headline = (a.content_body.split(". ")[0] + ".") || "Untitled";
                    const summary = a.content_body.substring(headline.length).trim() || a.content_body;
                    return (
                      <Card key={i} className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <Badge variant="neutral" className="text-xs">{sourceLabel}</Badge>
                              <span className="text-xs text-muted-foreground">
                                {a.normalized_calendar_date || a.ingest_date || "Unknown date"}
                              </span>
                            </div>
                            <div className="font-semibold text-sm text-foreground mb-2 leading-tight">{headline}</div>
                            <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">{summary}</p>
                            {a.url && (
                              <a href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-1">
                                <ExternalLink size={12} />
                                View article
                              </a>
                            )}
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                  {news.length === 0 && !detailsLoading && (
                    <p className="text-xs text-muted-foreground">No news articles found for {t.symbol}.</p>
                  )}
                </div>
              </div>

              {/* Recent SEC Filings - REAL DATA */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Recent SEC Filings</h3>
                  <span className="text-xs text-muted-foreground">{filings.length} filings found</span>
                </div>
                <div className="space-y-2">
                  {filings.map((f, i) => (
                    <div key={i} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="neutral" className="text-xs font-mono">{f.form_type}</Badge>
                          <span className="text-xs text-muted-foreground">
                            {f.filing_date ? `Filed ${f.filing_date}` : f.period_of_report ? `Period ending ${f.period_of_report}` : "Date not recorded"}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          Accession: {f.accession_number}
                        </div>
                      </div>
                      {f.accession_number && (
                        <div className="flex items-center gap-3 shrink-0">
                          {/* Our rendered copy (read-only, sandboxed); v=2 skips copies cached as plain text */}
                          <a href={`/api/tickers/${t.symbol}/filings/${f.accession_number.replace(/-/g, "")}/content?cik=${f.target_cik}&v=2`} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-400 hover:text-blue-300">
                            View
                          </a>
                          {/* The filing on SEC.gov itself */}
                          {f.url && (
                            <a href={f.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300">
                              <ExternalLink size={12} />
                              SEC.gov
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {filings.length === 0 && !detailsLoading && (
                    <p className="text-xs text-muted-foreground">No SEC filings found for {t.symbol}.</p>
                  )}
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Key Financials - REAL DATA (from prices endpoint) */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Key Financials</h3>
                <div className="space-y-2 text-sm">
                  {financials ? (
                    [
                      { label: "Current Price", value: `$${formatPrice(financials.currentPrice)}`, source: "Latest" },
                      { label: "Previous Close", value: `$${formatPrice(financials.previousClose)}`, source: "Prior session" },
                      { label: "Open", value: `$${formatPrice(financials.open)}`, source: "Latest session" },
                      { label: "High", value: `$${formatPrice(financials.high)}`, source: "Latest session" },
                      { label: "Low", value: `$${formatPrice(financials.low)}`, source: "Latest session" },
                      { label: "Daily Change", value: financials.dailyChange !== null ? `${financials.dailyChange > 0 ? "+" : ""}${financials.dailyChange.toFixed(2)}%` : "—", source: "Latest session" },
                    ].map(f => (
                      <div key={f.label} className="flex items-center justify-between py-1 border-b border-border/30 last:border-0">
                        <span className="text-muted-foreground text-xs">{f.label}</span>
                        <div className="text-right">
                          <span className="font-mono text-xs text-foreground font-semibold">{f.value}</span>
                          <Badge variant="neutral" className="ml-1 text-xs">{f.source}</Badge>
                        </div>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-muted-foreground">{detailsLoading ? "Loading prices…" : `No price data available for ${t.symbol}.`}</p>
                  )}
                </div>
              </Card>

              {/* Quick actions */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                <div className="space-y-1.5">
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Bell size={12} />} onClick={() => onSetAlert(ticker)}>Set Alert</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Briefcase size={12} />} onClick={openWorkspacePicker}>Add to Workspace</Btn>
                </div>
              </Card>
            </div>
          </div>
        )}

        {tab === "news" && (
          // Paged: 20 per page, any date range back to the ticker's earliest article.
          <TickerNewsFeed ticker={ticker} firebaseUser={firebaseUser} />
        )}

      </div>
      {pickWorkspace && (
        <Modal title={`Add ${ticker} to a workspace`} onClose={() => setPickWorkspace(false)}>
          {workspaces === null ? (
            <p className="text-sm text-muted-foreground">Loading workspaces…</p>
          ) : workspaces.length === 0 ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">You don't have any workspaces yet.</p>
              <Btn variant="primary" size="sm" onClick={() => { setPickWorkspace(false); navigate("workspaces"); }}>Create a workspace</Btn>
            </div>
          ) : (
            <div className="space-y-2">
              {workspaces.map(ws => (
                <button key={ws.id} onClick={() => addToWorkspace(ws)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-border hover:border-primary/40 hover:bg-secondary/40 text-left cursor-pointer">
                  <span className="text-sm text-foreground">{ws.name}</span>
                  <span className="text-xs text-muted-foreground">{ws.tickers.includes(ticker) ? "Added" : `${ws.tickers.length} tickers`}</span>
                </button>
              ))}
            </div>
          )}
          {wsMessage && <p className="text-xs text-muted-foreground mt-3">{wsMessage}</p>}
        </Modal>
      )}
    </div>
  );
}

export default TickerDashboard;
