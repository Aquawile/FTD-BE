import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, ScorePill, cn, getHypeColor, getEvidenceColor } from "../ui";
import { AlertTriangle, Bell, Briefcase, CheckCircle, Download, ExternalLink, Flag, Info, Maximize2, Sparkles, TrendingDown, TrendingUp } from "lucide-react";
import { TICKERS } from "../../mockData";

interface NewsArticle {
  id: number;
  ticker: string;
  headline: string;
  source: string;
  time: string;
  summary: string;
  hype: number;
  evidence: number;
  claims: string[];
  evidenceLinks: string[];
  flagged: boolean;
}
import { apiRequest } from "../../api";

interface TrackedTicker {
  symbol: string;
  name: string;
  sector: string | null;
  current_price: number | null;
  evidence_score: number | null;
  hype_score: number | null;
  change_percent: number | null;
  price_as_of: string | null;
}

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
  element_count: number;
  url: string | null;
}

interface TickerData {
  symbol: string;
  name: string;
  sector: string;
  hype: number;
  evidence: number;
  price: number;
  change: number;
}

function TickerDashboard({ navigate, ticker, firebaseUser, onReport }: { navigate: (p: Page) => void; ticker: string; firebaseUser: FirebaseUser | null; onReport: () => void }) {
  const [tab, setTab] = useState("overview");
  const [tickerData, setTickerData] = useState<TickerData | null>(null);
  const [prices, setPrices] = useState<PriceRow[]>([]);
  const [news, setNews] = useState<NewsRow[]>([]);
  const [articles, setArticles] = useState<NewsArticle[]>([]);
  const [filings, setFilings] = useState<FilingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const tabs = ["overview", "news", "evidence"];

  const mockTicker = TICKERS.find(t => t.symbol === ticker) || TICKERS[0];

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      if (!firebaseUser) {
        setTickerData({
          symbol: ticker,
          name: mockTicker.name,
          sector: mockTicker.sector,
          hype: mockTicker.hype,
          evidence: mockTicker.evidence,
          price: mockTicker.price,
          change: mockTicker.change,
        });
        setArticles(NEWS_ARTICLES.filter(a => a.ticker === ticker || a.ticker === ticker.slice(0, 3)));
        setLoading(false);
        return;
      }
      try {
        const today = new Date();
        const start = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
        const end = today.toISOString().split("T")[0];

        const [pricesRes, newsRes, filingsRes] = await Promise.all([
          apiRequest(`/tickers/${ticker}/prices?start=${start}&end=${end}`, firebaseUser),
          apiRequest(`/tickers/${ticker}/news?start=${start}&end=${end}&limit=50`, firebaseUser),
          apiRequest(`/tickers/${ticker}/filings`, firebaseUser),
        ]);

        if (!cancelled) {
          if (pricesRes.ok) {
            const priceData: PriceRow[] = await pricesRes.json();
            setPrices(priceData);
            const latest = priceData[priceData.length - 1];
            if (latest) {
              setTickerData({
                symbol: ticker,
                name: mockTicker.name,
                sector: mockTicker.sector,
                hype: mockTicker.hype,
                evidence: mockTicker.evidence,
                price: Number(latest.current ?? mockTicker.price),
                change: Number(latest.percent_change ?? mockTicker.change),
              });
            }
          }
          if (newsRes.ok) {
            const newsData: NewsRow[] = await newsRes.json();
            setNews(newsData);
          }
          if (filingsRes?.ok) {
            const filingsData: FilingSummary[] = await filingsRes.json();
            setFilings(filingsData.slice(0, 10));
          }
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [ticker, firebaseUser, mockTicker]);

  const t = tickerData || {
    symbol: ticker,
    name: mockTicker.name,
    sector: mockTicker.sector,
    hype: mockTicker.hype,
    evidence: mockTicker.evidence,
    price: mockTicker.price,
    change: mockTicker.change,
  };

  const flagArticle = (id: number) => setArticles(prev => prev.map(a => a.id === id ? { ...a, flagged: !a.flagged } : a));

  const formatPrice = (price: number | null) => {
    if (price === null) return "—";
    return price.toLocaleString();
  };

  const getFinancialFromPrices = () => {
    if (prices.length === 0) return null;
    const latest = prices[prices.length - 1];
    const prev = prices[prices.length - 2];
    return {
      currentPrice: latest.current ?? null,
      previousClose: latest.previous_close ?? null,
      open: latest.open ?? null,
      high: latest.high ?? null,
      low: latest.low ?? null,
      dailyChange: latest.percent_change != null ? parseFloat(latest.percent_change) : null,
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
                <Badge variant="neutral">{t.sector}</Badge>
                <Badge variant="neutral">NASDAQ</Badge>
              </div>
              <div className="text-muted-foreground text-sm">{t.name}</div>
              <div className="flex items-center gap-4 mt-2">
                <span className="font-mono font-bold text-xl text-foreground">${t.price.toLocaleString()}</span>
                <span className={cn("flex items-center gap-1 text-sm", t.change > 0 ? "text-emerald-400" : "text-red-400")}>
                  {t.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {t.change > 0 ? "+" : ""}{t.change}%
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3">
              <Btn variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>Set Alert</Btn>
              <Btn variant="secondary" size="sm" icon={<Briefcase size={12} />} onClick={() => navigate("workspaces")}>Add to Workspace</Btn>
              <Btn variant="secondary" size="sm" icon={<Maximize2 size={12} />} onClick={() => navigate("ticker-comparison")}>Compare</Btn>
            </div>
            <div className="flex items-center gap-6">
              <ScorePill label="Hype Score" score={t.hype} type="hype" />
              <ScorePill label="Evidence Score" score={t.evidence} type="evidence" />
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
              {/* AI Summary - PLACEHOLDER */}
              <Card className="p-5 border-purple-500/20 bg-gradient-to-r from-purple-500/5 to-transparent">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={14} className="text-purple-400" />
                  <span className="text-sm font-semibold text-foreground">AI Research Summary</span>
                  <Badge variant="neutral">PLACEHOLDER</Badge>
                </div>
                <p className="text-sm text-muted-foreground italic">AI research summary generation is not yet available. This will be populated with AI-generated insights once the inference engine is deployed.</p>
              </Card>

              {/* Key claims - PLACEHOLDER */}
              <div>
                <h3 className="font-semibold mb-3">Key Claims in Circulation</h3>
                <Card className="p-4">
                  <p className="text-sm text-muted-foreground italic">Claims extraction from news and social data is not yet available. This section will display claims extracted from real articles with evidence scoring once the pipeline is processing data for this ticker.</p>
                </Card>
              </div>

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
                  {news.length === 0 && !loading && (
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
                          <span className="text-xs text-muted-foreground">{f.filing_date || "Unknown date"}</span>
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          Accession: {f.accession_number}
                        </div>
                      </div>
                      {f.url && (
                        <a href={`/api/tickers/${t.symbol}/filings/${f.accession_number.replace(/-/g, "")}/content?cik=${f.target_cik}`} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 shrink-0">
                          <ExternalLink size={12} />
                          SEC.gov
                        </a>
                      )}
                    </div>
                  ))}
                  {filings.length === 0 && !loading && (
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
                      { label: "Previous Close", value: `$${formatPrice(financials.previousClose)}`, source: "Prior Day" },
                      { label: "Open", value: `$${formatPrice(financials.open)}`, source: "Today" },
                      { label: "High", value: `$${formatPrice(financials.high)}`, source: "Today" },
                      { label: "Low", value: `$${formatPrice(financials.low)}`, source: "Today" },
                      { label: "Daily Change", value: financials.dailyChange !== null ? `${financials.dailyChange > 0 ? "+" : ""}${financials.dailyChange.toFixed(2)}%` : "—", source: "Today" },
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
                    <p className="text-xs text-muted-foreground">No price data available for {t.symbol}.</p>
                  )}
                </div>
              </Card>

              {/* Source breakdown - PLACEHOLDER */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Source Breakdown</h3>
                <p className="text-xs text-muted-foreground italic">Source breakdown is not yet available. This will show the count of data points from each source (SEC filings, news, etc.) when the analytics pipeline is active.</p>
              </Card>

              {/* Quick actions */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                <div className="space-y-1.5">
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>Set Alert</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Briefcase size={12} />} onClick={() => navigate("workspaces")}>Add to Workspace</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-comparison")}>Export Report</Btn>
                </div>
              </Card>
            </div>
          </div>
        )}

        {tab === "news" && (
           <div className="space-y-3">
             <h3 className="font-semibold">All News for {t.symbol}</h3>
             {news.length > 0 ? (
              news.map((a, i) => {
                const sourceLabel = a.source === "gnews" ? "Google News" : a.source === "finnhub" ? "Finnhub" : a.source === "sec" ? "SEC" : a.source || "News";
                const headline = (a.content_body.split(". ")[0] + ".") || "Untitled";
                const summary = a.content_body.substring(headline.length).trim() || a.content_body;
                return (
                  <Card key={`api-${i}`} className="p-5">
                    <div className="flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="neutral" className="text-xs">{sourceLabel}</Badge>
                          <span className="text-xs text-muted-foreground">{a.normalized_calendar_date || a.ingest_date || "Unknown date"}</span>
                        </div>
                        <h4 className="font-semibold text-sm text-foreground mb-2 leading-snug">{headline}</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">{summary}</p>
                        {a.url && (
                          <a href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2">
                            <ExternalLink size={12} />
                            View article
                          </a>
                        )}
                      </div>
                    </div>
                  </Card>
                );
              })
            ) : (
              articles.map(a => (
                <Card key={a.id} className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="neutral" className="text-xs">{a.source}</Badge>
                        <span className="text-xs text-muted-foreground">{a.time}</span>
                        {a.flagged && <Badge variant="hype" className="text-xs"><Flag size={8} /> Reported</Badge>}
                      </div>
                      <h4 className="font-semibold text-sm text-foreground mb-2 leading-snug">{a.headline}</h4>
                      <p className="text-xs text-muted-foreground leading-relaxed">{a.summary}</p>
                      {a.claims.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {a.claims.map(c => <Badge key={c} variant="outline" className="text-xs">{c}</Badge>)}
                        </div>
                      )}
                      {a.evidenceLinks.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {a.evidenceLinks.map(l => <Badge key={l} variant="evidence" className="text-xs"><ExternalLink size={8} /> {l}</Badge>)}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <div className="text-right space-y-1">
                        <div className="text-xs text-muted-foreground">Hype</div>
                        <div className="font-mono text-sm font-bold" style={{ color: getHypeColor(a.hype) }}>{a.hype}</div>
                      </div>
                      <div className="text-right space-y-1">
                        <div className="text-xs text-muted-foreground">Evidence</div>
                        <div className="font-mono text-sm font-bold" style={{ color: getEvidenceColor(a.evidence) }}>{a.evidence}</div>
                      </div>
                      <button
                        onClick={() => { flagArticle(a.id); onReport(); }}
                        className={cn("mt-2 p-2 rounded-lg border transition-all cursor-pointer", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400" : "border-border text-muted-foreground hover:text-orange-400 hover:border-orange-500/30")}
                      >
                        <Flag size={13} />
                      </button>
                    </div>
                  </div>
                </Card>
              ))
            )}
            {news.length === 0 && articles.length === 0 && (
              <p className="text-xs text-muted-foreground">No articles found for {t.symbol}.</p>
            )}
          </div>
        )}

        {tab === "evidence" && (
          <div className="space-y-5">
            <Card className="p-5">
              <h3 className="font-semibold mb-4">Evidence Breakdown Matrix</h3>
              <div className="space-y-4">
                {[
                  { category: "SEC Filings & XBRL Data", score: 94, count: "12 filings", description: "All major financial disclosures verified and parsed. Revenue, margin, and segment data fully corroborated." },
                  { category: "Analyst Reports", score: 72, count: "28 reports", description: "Sell-side consensus moderately evidenced. Price targets range 20–150% above current price with mixed backing." },
                  { category: "News Articles", score: 61, count: "847 articles", description: "Mainstream financial news mostly factual with selective embellishment in headlines." },
                  { category: "Community / Reddit", score: 23, count: "2,341 posts", description: "Heavy speculative content. Most high-engagement posts lack quantitative financial evidence." },
                ].map(e => (
                  <div key={e.category} className="p-4 bg-secondary/30 rounded-xl border border-border/50">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium text-sm text-foreground">{e.category}</span>
                        <span className="text-xs text-muted-foreground ml-2">{e.count}</span>
                      </div>
                      <span className="font-mono font-bold text-sm" style={{ color: getEvidenceColor(e.score) }}>{e.score}/100</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden mb-2">
                      <div className="h-full rounded-full transition-all" style={{ width: `${e.score}%`, background: getEvidenceColor(e.score) }} />
                    </div>
                    <p className="text-xs text-muted-foreground">{e.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

export default TickerDashboard;
