import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn, getHypeColor, getEvidenceColor } from "../ui";
import { ChevronLeft, Plus, Sparkles } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function ComparisonPage({ navigate }: { navigate: (p: Page) => void }) {
  const tickers = [TICKERS[0], TICKERS[1], TICKERS[4]]; // NVDA, TSLA, AMD
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("dashboard")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Dashboard</button>
        <h1 className="text-xl font-bold flex-1">Multi-Ticker Comparison</h1>
        <Btn variant="secondary" size="sm" icon={<Plus size={12} />}>Add Ticker</Btn>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {tickers.map(t => (
          <div key={t.symbol} className="space-y-4">
            <Card className="p-4 border-t-2" style={{ borderTopColor: t.symbol === "NVDA" ? "#3B82F6" : t.symbol === "TSLA" ? "#F59E0B" : "#8B5CF6" }}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
                  <span className="font-mono font-bold text-sm">{t.symbol.slice(0, 2)}</span>
                </div>
                <div>
                  <div className="font-mono font-bold text-foreground">{t.symbol}</div>
                  <div className="text-xs text-muted-foreground">{t.name}</div>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Hype Score</span><span className="font-mono" style={{ color: getHypeColor(t.hype) }}>{t.hype}</span></div>
                  <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.hype}%`, background: getHypeColor(t.hype) }} /></div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Evidence Score</span><span className="font-mono" style={{ color: getEvidenceColor(t.evidence) }}>{t.evidence}</span></div>
                  <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.evidence}%`, background: getEvidenceColor(t.evidence) }} /></div>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground pt-1 border-t border-border">
                  <span>Gap (H-E)</span>
                  <span className={cn("font-mono", (t.hype - t.evidence) > 20 ? "text-orange-400" : "text-emerald-400")}>{t.hype - t.evidence > 0 ? "+" : ""}{t.hype - t.evidence}</span>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="space-y-2 text-xs">
                {[{ l: "Price", v: `$${t.price}` }, { l: "24h Change", v: `${t.change > 0 ? "+" : ""}${t.change}%` }, { l: "Sector", v: t.sector }].map(r => (
                  <div key={r.l} className="flex justify-between"><span className="text-muted-foreground">{r.l}</span><span className="font-mono text-foreground">{r.v}</span></div>
                ))}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-semibold mb-2">AI Verdict</div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {t.symbol === "NVDA" ? "Strong evidence base with moderate hype premium. Core financial claims well-corroborated by SEC filings." : t.symbol === "TSLA" ? "High speculative premium. FSD autonomy claims significantly outpace regulatory disclosures." : "Competitive claims against NVDA partially verified in benchmark data but market position claims overstated."}
              </p>
            </Card>
          </div>
        ))}
      </div>
      <Card className="mt-6 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={14} className="text-purple-400" />
          <h3 className="font-semibold text-sm">AI Comparative Summary</h3>
          <Badge variant="purple">Multi-hop RAG</Badge>
        </div>
        <p className="text-sm text-foreground/90 leading-relaxed">
          Across the three analyzed tickers, <strong className="text-foreground">NVDA</strong> maintains the strongest evidence-to-hype ratio (gap: +13). <strong className="text-foreground">TSLA</strong> carries the highest risk premium relative to disclosed evidence (gap: +43), with FSD monetization claims unverified in SEC filings. <strong className="text-foreground">AMD</strong> occupies a middle position with competitive benchmark claims partially corroborated but market share projections speculative. Investors seeking evidence-backed exposure should prioritize NVDA and MSFT (not shown) over TSLA and PLTR.
        </p>
        <div className="mt-3 flex gap-2">
          <Badge variant="evidence">3 sources retrieved</Badge>
          <Badge variant="neutral">SEC EDGAR · Analyst Notes · Community</Badge>
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 14: Workspaces
// ────────────────────────────────────────────────

export default ComparisonPage;
