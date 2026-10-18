import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, HypeEvidenceBar, getHypeColor, getEvidenceColor } from "../ui";
import { ArrowRight, BarChart, Sparkles, TrendingUp } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../mockData";

function LegacyLandingPage({ navigate }: { navigate: (p: Page) => void }) {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <BarChart size={16} className="text-white" />
          </div>
          <span className="font-bold text-xl text-foreground tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          <Badge variant="purple" className="ml-1">Beta</Badge>
        </div>
        <div className="flex items-center gap-3">
          <Btn variant="ghost" onClick={() => navigate("login")}>Sign In</Btn>
          <Btn variant="primary" onClick={() => navigate("register")}>Get Started Free</Btn>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-8 pt-24 pb-20 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <Badge variant="purple" className="mb-4 text-sm px-3 py-1">
          <Sparkles size={12} /> AI-Powered Research
        </Badge>
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 max-w-4xl mx-auto" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Separate{" "}
          <span style={{ color: "#F59E0B" }}>Hype</span>
          {" "}from{" "}
          <span style={{ color: "#10B981" }}>Evidence</span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
          FTD aggregates financial news, SEC filings, and community discussions — then uses AI to score every claim on an evidence scale. Stop guessing. Start researching.
        </p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Btn variant="primary" size="lg" onClick={() => navigate("register")} icon={<ArrowRight size={16} />}>
            Start Researching
          </Btn>
          <Btn variant="outline" size="lg" onClick={() => navigate("login")}>
            View Demo
          </Btn>
        </div>
      </section>

      {/* Demo Preview Card */}
      <section className="px-8 pb-16 max-w-5xl mx-auto">
        <div className="relative rounded-2xl border border-border/50 overflow-hidden bg-card/50 backdrop-blur shadow-2xl shadow-black/30">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50 bg-card/80">
            <div className="flex gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-red-500/70" /><div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" /><div className="w-2.5 h-2.5 rounded-full bg-green-500/70" /></div>
            <span className="text-xs text-muted-foreground mx-auto">ftd.research — NVDA Dashboard</span>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xl text-foreground">NVDA</span>
                    <Badge variant="neutral">NASDAQ</Badge>
                  </div>
                  <div className="text-muted-foreground text-sm mt-0.5">NVIDIA Corporation</div>
                </div>
                <div className="text-right">
                <div className="font-mono font-bold text-lg text-foreground">$873.50</div>
                <div className="text-emerald-400 text-sm flex items-center gap-1 justify-end"><TrendingUp size={12} />+4.2%</div>
                </div>
              </div>
                <HypeEvidenceBar hype={84} evidence={71} />
              {NEWS_ARTICLES.slice(0, 2).map(a => (
                <div key={a.id} className="flex items-start gap-3 p-3 bg-secondary/50 rounded-lg border border-border/50">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-muted-foreground mb-1">{a.source} · {a.time}</div>
                    <div className="text-sm font-medium text-foreground truncate">{a.headline}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-xs font-mono" style={{ color: getHypeColor(a.hype) }}>H:{a.hype}</span>
                    <span className="text-xs font-mono" style={{ color: getEvidenceColor(a.evidence) }}>E:{a.evidence}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="p-3 bg-secondary/50 rounded-lg border border-border/50">
                <div className="text-xs text-muted-foreground mb-2">Hype vs Evidence</div>
                <div className="text-3xl font-mono font-bold" style={{ color: "#F59E0B" }}>84</div>
                <div className="text-xs text-muted-foreground">vs. Evidence <span style={{ color: "#10B981" }}>71</span></div>
              </div>
              <div className="p-3 bg-secondary/50 rounded-lg border border-border/50">
                <div className="text-xs text-muted-foreground mb-2">AI Summary</div>
                <div className="text-xs text-foreground leading-relaxed">Blackwell GPU production claims are partially corroborated by TSMC supply chain data, but $2000 PT targets lack quantitative support.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-8 pb-20 max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12" style={{ fontFamily: "'Outfit', sans-serif" }}>Everything a serious researcher needs</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: BarChart2, title: "Hype vs. Evidence Scoring", desc: "Every article and claim scored on a 0–100 evidence scale, aggregated from news, filings, and community.", color: "#F59E0B" },
            { icon: FileText, title: "SEC Filing Integration", desc: "Automatically parsed 10-K, 10-Q, and 8-K filings with XBRL data extraction and section mapping.", color: "#10B981" },
            { icon: MessageSquare, title: "AI Multi-Hop Queries", desc: "Ask complex comparative questions across multiple tickers. The AI decomposes, retrieves, and synthesizes with source attribution.", color: "#8B5CF6" },
            { icon: Clock, title: "Narrative Timelines", desc: "Chronological view of how a thesis evolved over time — from early Reddit speculation to confirmed SEC disclosures.", color: "#0EA5E9" },
            { icon: Briefcase, title: "Research Workspaces", desc: "Group up to 50 tickers into themed research workspaces. Track them all together with workspace-level scoring.", color: "#3B82F6" },
            { icon: AlertTriangle, title: "Narrative Shift Alerts", desc: "Get notified when Hype vs. Evidence deltas exceed 10 points — catch narrative reversals before the crowd.", color: "#EF4444" },
          ].map(f => (
            <Card key={f.title} className="p-5">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: `${f.color}15` }}>
                <f.icon size={20} style={{ color: f.color }} />
              </div>
              <h3 className="font-semibold text-foreground mb-2 text-sm">{f.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{f.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-8 pb-20 text-center">
        <div className="max-w-xl mx-auto p-10 bg-gradient-to-br from-primary/10 to-accent/5 rounded-2xl border border-primary/20">
          <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: "'Outfit', sans-serif" }}>Start your research today</h2>
          <p className="text-muted-foreground mb-6 text-sm">Free access during beta. No credit card required.</p>
          <Btn variant="primary" size="lg" onClick={() => navigate("register")}>Create Free Account</Btn>
        </div>
      </section>
    </div>
  );
}

export default LegacyLandingPage;
