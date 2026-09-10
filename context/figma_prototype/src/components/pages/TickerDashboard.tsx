// ────────────────────────────────────────────────
// TICKER DASHBOARD PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { useTickerDashboard } from "../hooks";
import { Card, Badge, Button as Btn, Tab, Tabs, TabsList, TabsTrigger, TabsContent, Card, Sparkline, Badge, Button as Btn, ChevronRight, TrendingUp, TrendingDown, Flag, AlertCircle, Sparkles, FileText, Activity, Users, Globe, BarChart2, ChevronRight, CheckCircle, AlertTriangle, Info, Flag, ExternalLink, Bell, Briefcase, Plus, Maximize2, Search, Filter } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface TickerDashboardProps {
  ticker: string;
  navigate: (p: string) => void;
  onReport: () => void;
  setSelectedTicker: (t: string) => void;
}

export function TickerDashboard({ ticker, navigate, onReport, setSelectedTicker }: TickerDashboardProps) {
  const [tab, setTab] = useState("overview");
  const [articles, setArticles] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [filings, setFilings] = useState<any[]>([]);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [trackedTickers, setTrackedTickers] = useState<any[]>([]);

  const { articles: liveArticles, loading: newsLoading, error: newsError } = useTickerNews(ticker);
  const { timeline: liveTimeline, loading: timelineLoading, error: timelineError } = useTickerTimeline(ticker);
  const { filings: liveFilings, loading: filingsLoading, error: filingsError } = useTickerFilings(ticker);
  const { evidence: liveEvidence, loading: evidenceLoading, error: evidenceError } = useTickerEvidence(ticker);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetch(`/api/tickers/${ticker}/news`).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(`/api/tickers/${ticker}/timeline`).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(`/api/tickers/${ticker}/filings`).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(`/api/tickers/${ticker}/evidence`).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(`/api/tickers/tracked`).then(r => r.ok ? r.json() : []).catch(() => []),
    ])
      .then(([news, timeline, filings, evidence, tracked]) => {
        setArticles(news.map((n: any, i: number) => ({
          id: i,
          source: n.source || "GNews",
          time: n.ingest_date || new Date().toLocaleDateString(),
          headline: n.content_body?.slice(0, 120) || "No headline",
          summary: n.content_body || "",
          claims: [],
          evidenceLinks: [],
          hype: Math.floor(Math.random() * 20) + 50,
          evidence: Math.floor(Math.random() * 30) + 40,
          flagged: false,
        }));
        setTimeline(timeline);
        setFilings(filings);
        setEvidence(evidence);
      })
      .finally(() => setLoading(false));
  }, [ticker]);

  const t = { symbol: "NVDA", name: "NVIDIA Corporation", hype: 84, evidence: 71, sector: "Semiconductors", change: 4.2, price: 873.50 };
  const tabs = ["overview", "news", "evidence", "community", "filings", "timeline"];

  const flagArticle = (id: number) => setArticles(prev => prev.map(a => a.id === id ? { ...a, flagged: !a.flagged } : a));
  const spData = [45, 52, 48, 63, 71, 68, 74, 69, 77, 82, 79, 84];

  const getHypeColor = (h: number) => h > 70 ? "#F59E0B" : h > 40 ? "#F59E0B" : "#EF4444";
  const getEvidenceColor = (e: number) => e > 70 ? "#10B981" : e > 40 ? "#F59E0B" : "#EF4444";

  const tabs = ["overview", "news", "evidence", "community", "filings", "timeline"];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-card border-b border-border px-6 py-5">
        <div className="flex items-start justify-between gap-4 max-w-7xl mx-auto">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center shrink-0">
              <span className="font-mono font-bold text-lg text-foreground">NVDA</span>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold font-mono text-foreground">NVDA</h1>
                <Badge variant="neutral">Semiconductors</Badge>
                <Badge variant="neutral">NASDAQ</Badge>
              </div>
              <div className="text-muted-foreground text-sm mt-1">NVIDIA Corporation</div>
              <div className="flex items-center gap-4 mt-2">
                <span className="font-mono font-bold text-xl text-foreground">$873.50</span>
                <span className="flex items-center gap-1 text-sm font-semibold text-emerald-400"><TrendingUp size={14} /> +4.2%</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3">
              <Button variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>Set Alert</Button>
              <Button variant="secondary" size="sm" icon={<Briefcase size={12} />} onClick={() => navigate("workspaces")}>Add to Workspace</Button>
              <Button variant="secondary" size="sm" icon={<Maximize2 size={12} />} onClick={() => navigate("ticker-comparison")}>Compare</Button>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-xs text-muted-foreground">Hype Score</div>
                <div className="font-mono text-xl font-bold text-orange-400">84</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-muted-foreground">Evidence Score</div>
                <div className="font-mono text-xl font-bold text-emerald-400">71</div>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-0 mt-5 max-w-7xl mx-auto border-b border-transparent -mb-5">
          {["overview", "news", "evidence", "community", "filings", "timeline"].map(tab => (
            <button
              key={tab}
              onClick={() => setTab(tab)}
              className={`px-4 py-2 text-sm border-b-2 transition-all cursor-pointer capitalize`,
                tab === "overview" ? "border-primary text-primary font-medium" : "border-transparent text-muted-foreground hover:text-foreground"
              }
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 max-w-7xl mx-auto w-full">
        {tab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main col */}
            <div className="lg:col-span-2 space-y-4">
              {/* AI Summary */}
              <div className="border-purple-500/20 bg-gradient-to-r from-purple-500/5 to-transparent p-5 rounded-xl border border-purple-500/20">
                <div className="flex items-center gap-2 mb-3">
                  <span className="font-semibold text-foreground">AI Research Summary</span>
                  <Badge variant="purple">Updated 2h ago</Badge>
                </div>
                <p className="text-sm text-foreground/90 leading-relaxed">
                  NVIDIA's position in the AI chip market is substantially supported by verifiable financial disclosures. 
                  The Q1 FY2025 earnings beat ($26.04B revenue, 78% gross margin) and confirmed Blackwell production ramp provide strong evidence for near-term demand claims. 
                  However, community-driven price targets ($1,200–$2,000) significantly outpace disclosed guidance and carry near-zero evidentiary basis. 
                  The 13-point gap between Hype (84) and Evidence (71) reflects speculative premium above confirmed fundamentals.
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <Badge variant="evidence"><CheckCircle size={10} /> 3 confirmed claims</Badge>
                  <Badge variant="hype"><AlertTriangle size={10} /> 2 unverified claims</Badge>
                  <Badge variant="neutral"><Info size={10} /> 1 under review</Badge>
                </div>
              </div>

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
                      <div className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{
                        backgroundColor: c.evidence === "confirmed" ? "#10B981" : c.evidence === "high" ? "#3B82F6" : c.evidence === "medium" ? "#F59E0B" : "#EF4444"
                      }} />
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm text-foreground">{c.claim}</div>
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
                  <h3 className="font-semibold text-foreground">Recent News & Analysis</h3>
                  <button onClick={() => setTab("news")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
                </div>
                <div className="space-y-3">
                  {newsData.map(a => (
                    <div key={a.id} className="flex items-start gap-3 p-4 bg-secondary/30 rounded-xl border border-border/50 group">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-semibold text-sm text-foreground">NVDA</span>
                          <span className="text-muted-foreground text-xs truncate">{a.source}</span>
                        </div>
                        <div className="mt-1.5 flex items-center gap-3">
                          <div className="text-xs text-muted-foreground">
                            Hype
                          </div>
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
              <div className="space-y-4">
                <div className="p-4 bg-secondary/30 rounded-xl border border-border/50">
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
                          <span className="font-mono text-sm font-semibold text-foreground">${f.value}</span>
                          <Badge variant="neutral" className="ml-1 text-xs">{f.source}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>

              {/* Source breakdown */}
              <div>
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
              </div>

              {/* Quick actions */}
              <div>
                <Card className="p-4">
                  <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                  <div className="space-y-1.5">
                    <Button variant="secondary" size="sm" className="w-full" icon={<Clock size={12} />} onClick={() => navigate("ticker-timeline")}>View Timeline</Button>
                    <Button variant="secondary" size="sm" className="w-full" icon={<FileText size={12} />} onClick={() => navigate("ticker-filings")}>SEC Filings</Button>
                    <Button variant="secondary" size="sm" className="w-full" icon={<Users size={12} />} onClick={() => navigate("ticker-community")}>Community Sentiment</Button>
                    <Button variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-timeline")}>Export Report</Button>
                  </div>
                </Card>
              </div>
            </div>
          </div>
        )}

        {tab === "news" && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-foreground">Recent News & Analysis</h2>
                <button onClick={() => setTab("news")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
              </div>
              <div className="space-y-3">
                {articles.map(a => (
                  <Card key={a.id} className="p-5">
                    <div className="flex items-start gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-mono font-semibold text-sm text-foreground">{a.symbol}</span>
                          <span className="text-muted-foreground text-xs truncate">{a.source}</span>
                        </div>
                        <h4 className="font-semibold text-sm text-foreground mb-2">{a.headline}</h4>
                        <p className="text-xs text-muted-foreground leading-relaxed">{a.summary}</p>
                        <div className="mt-2 flex items-center gap-3">
                          <div className="flex items-center gap-1">
                            <span className="font-mono text-xs text-emerald-400">H:{a.hype}</span>
                            <span className="font-mono text-xs" style={{ color: getEvidenceColor(a.evidence) }}>E:{a.evidence}</span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={() => { flagArticle(a.id); onReport(); }}
                        className={cn("p-1.5 rounded-lg border transition-all cursor-pointer opacity-0 group-hover:opacity-100", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400 opacity-100" : "border-border text-muted-foreground hover:border-orange-500/30 hover:text-orange-400")}
                        title="Report incorrect mapping"
                      >
                        <Flag size={13} />
                      </button>
                    </div>
                  ))}
              </div>
            </div>
        )}
      </div>
    </div>
  );
}

export default TickerDashboard;