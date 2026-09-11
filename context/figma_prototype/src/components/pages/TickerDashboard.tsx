import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, ScorePill, cn, getHypeColor, getEvidenceColor } from "../ui";
import { AlertTriangle, Bell, Briefcase, CheckCircle, Clock, Download, ExternalLink, FileText, Flag, Info, Maximize2, Sparkles, TrendingDown, TrendingUp, Users } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";
import { apiRequest, API_BASE } from "../../api";

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
  const [articles, setArticles] = useState(NEWS_ARTICLES.map(a => ({ ...a })));
  const [tickerData, setTickerData] = useState<TickerData | null>(null);
  const [loading, setLoading] = useState(true);
  const tabs = ["overview", "news", "evidence", "community", "filings", "timeline"];

  const mockTicker = TICKERS.find(t => t.symbol === ticker) || TICKERS[0];

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      if (!firebaseUser) {
        setTickerData(mockTicker);
        setLoading(false);
        return;
      }
      try {
        const res = await apiRequest(`/tickers/${ticker}/prices`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          const latest = data[data.length - 1];
          const currentPrice = latest?.current ?? mockTicker.price;
          const prevClose = latest?.previous_close ?? mockTicker.price;
          const change = latest?.percent_change ?? mockTicker.change;
          setTickerData({
            symbol: ticker,
            name: mockTicker.name,
            sector: mockTicker.sector,
            hype: mockTicker.hype,
            evidence: mockTicker.evidence,
            price: Number(currentPrice),
            change: Number(change),
          });
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setTickerData(mockTicker);
          setLoading(false);
        }
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [ticker, firebaseUser, mockTicker]);

  const t = tickerData || mockTicker;

  const flagArticle = (id: number) => setArticles(prev => prev.map(a => a.id === id ? { ...a, flagged: !a.flagged } : a));

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
              onClick={() => { if (tab_ === "timeline") navigate("ticker-timeline"); else if (tab_ === "filings") navigate("ticker-filings"); else if (tab_ === "community") navigate("ticker-community"); else setTab(tab_); }}
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
              {/* AI Summary */}
              <Card className="p-5 border-purple-500/20 bg-gradient-to-r from-purple-500/5 to-transparent">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles size={14} className="text-purple-400" />
                  <span className="text-sm font-semibold text-foreground">AI Research Summary</span>
                  <Badge variant="purple">Updated 2h ago</Badge>
                </div>
                <p className="text-sm text-foreground/90 leading-relaxed">
                  NVIDIA's position in the AI chip market is substantially supported by verifiable financial disclosures. The Q1 FY2025 earnings beat ($26.04B revenue, 78% gross margin) and confirmed Blackwell production ramp provide strong evidence for near-term demand claims. However, community-driven price targets ($1,200–$2,000) significantly outpace disclosed guidance and carry near-zero evidentiary basis. The 13-point gap between Hype (84) and Evidence (71) reflects speculative premium above confirmed fundamentals.
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <Badge variant="evidence"><CheckCircle size={10} /> 3 confirmed claims</Badge>
                  <Badge variant="hype"><AlertTriangle size={10} /> 2 unverified claims</Badge>
                  <Badge variant="neutral"><Info size={10} /> 1 under review</Badge>
                </div>
              </Card>

              {/* Key claims */}
              <div>
                <h3 className="font-semibold mb-3">Key Claims in Circulation</h3>
                <div className="space-y-2">
                  {[
                    { claim: "Blackwell GPU production ahead of schedule by 18%", evidence: "high", source: "Q1 2024 Earnings Call + TSMC Report" },
                    { claim: "$40B+ data center backlog for H2 2024", evidence: "medium", source: "Analyst estimates — not disclosed in filings" },
                    { claim: "No viable GPU competitor for 3+ years", evidence: "low", source: "Social media consensus — not corroborated" },
                    { claim: "Data center revenue $18.4B, 427% YoY growth", evidence: "confirmed", source: "SEC 10-K Annual Filing CY2024" },
                  ].map(c => (
                    <div key={c.claim} className="flex items-start gap-3 p-3 bg-secondary/30 rounded-lg border border-border/50">
                      <div className={cn("w-2 h-2 rounded-full mt-1.5 shrink-0", c.evidence === "confirmed" ? "bg-emerald-400" : c.evidence === "high" ? "bg-blue-400" : c.evidence === "medium" ? "bg-yellow-400" : "bg-red-400")} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-foreground">{c.claim}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{c.source}</div>
                      </div>
                      <Badge variant={c.evidence === "confirmed" ? "evidence" : c.evidence === "high" ? "default" : c.evidence === "medium" ? "hype" : "danger"} className="shrink-0 text-xs capitalize">
                        {c.evidence}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recent news */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Recent News & Analysis</h3>
                  <button onClick={() => setTab("news")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
                </div>
                <div className="space-y-3">
                  {articles.slice(0, 3).map(a => (
                    <div key={a.id} className="flex items-start gap-3 p-4 bg-secondary/30 rounded-xl border border-border/50 group">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs text-muted-foreground">{a.source}</span>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">{a.time}</span>
                        </div>
                        <div className="text-sm font-medium text-foreground leading-tight mb-2">{a.headline}</div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono" style={{ color: getHypeColor(a.hype) }}>H:{a.hype}</span>
                          <span className="text-xs font-mono" style={{ color: getEvidenceColor(a.evidence) }}>E:{a.evidence}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => { flagArticle(a.id); onReport(); }}
                        className={cn("p-1.5 rounded-lg border transition-all cursor-pointer opacity-0 group-hover:opacity-100", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400 opacity-100" : "border-border text-muted-foreground hover:border-orange-500/30 hover:text-orange-400")}
                        title="Report incorrect mapping"
                      >
                        <Flag size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Financials */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Key Financials</h3>
                <div className="space-y-2 text-sm">
                  {[
                    { label: "Revenue (Q1 FY25)", value: "$26.04B", source: "10-Q" },
                    { label: "Gross Margin", value: "78.4%", source: "10-Q" },
                    { label: "EPS (diluted)", value: "$6.12", source: "10-Q" },
                    { label: "Data Center Rev.", value: "$22.6B", source: "10-Q" },
                    { label: "Market Cap", value: "$2.15T", source: "NASDAQ" },
                    { label: "P/E Ratio", value: "73.4x", source: "Derived" },
                  ].map(f => (
                    <div key={f.label} className="flex items-center justify-between py-1 border-b border-border/30 last:border-0">
                      <span className="text-muted-foreground text-xs">{f.label}</span>
                      <div className="text-right">
                        <span className="font-mono text-xs text-foreground font-semibold">{f.value}</span>
                        <Badge variant="neutral" className="ml-1 text-xs">{f.source}</Badge>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Source breakdown */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Source Breakdown</h3>
                <div className="space-y-2">
                  {[
                    { label: "SEC Filings", count: 12, color: "#10B981" },
                    { label: "News Articles", count: 847, color: "#3B82F6" },
                    { label: "Reddit Posts", count: 2341, color: "#F59E0B" },
                    { label: "Analyst Reports", count: 28, color: "#8B5CF6" },
                  ].map(s => (
                    <div key={s.label} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full" style={{ background: s.color }} />
                        <span className="text-muted-foreground">{s.label}</span>
                      </div>
                      <span className="font-mono text-foreground">{s.count.toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Quick actions */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                <div className="space-y-1.5">
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Clock size={12} />} onClick={() => navigate("ticker-timeline")}>View Timeline</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<FileText size={12} />} onClick={() => navigate("ticker-filings")}>SEC Filings</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Users size={12} />} onClick={() => navigate("ticker-community")}>Community Sentiment</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-timeline")}>Export Report</Btn>
                </div>
              </Card>
            </div>
          </div>
        )}

        {tab === "news" && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex gap-2">
                {["all", "news", "analysis", "reddit"].map(f => (
                  <button key={f} className="px-3 py-1 rounded-lg text-xs border border-border bg-secondary text-muted-foreground hover:text-foreground cursor-pointer capitalize">{f}</button>
                ))}
              </div>
              <div className="ml-auto text-xs text-muted-foreground">{articles.length} articles</div>
            </div>
            {articles.map(a => (
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
            ))}
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

// ────────────────────────────────────────────────
// PAGE 10: Narrative Timeline
// ────────────────────────────────────────────────

export default TickerDashboard;
