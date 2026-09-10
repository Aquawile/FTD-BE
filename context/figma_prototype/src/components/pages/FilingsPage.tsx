import { useState, useEffect } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn } from "../ui";
import { FileText, ExternalLink, CheckCircle, ChevronLeft } from "lucide-react";

export function FilingsPage({ navigate, ticker }: { navigate: (p: Page) => void; ticker: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  const filings = [
    { id: "f1", type: "10-Q", date: "May 22, 2024", period: "Q1 FY2025", size: "2.1MB", sections: 14, key: true },
    { id: "f2", type: "10-K", date: "Feb 26, 2024", period: "FY2024", size: "5.8MB", sections: 32, key: true },
    { id: "f3", type: "8-K", date: "May 21, 2024", period: "Earnings Release", size: "0.3MB", sections: 3, key: false },
    { id: "f4", type: "8-K", date: "Apr 30, 2024", period: "Executive Comp Update", size: "0.1MB", sections: 2, key: false },
    { id: "f5", type: "10-Q", date: "Nov 21, 2023", period: "Q3 FY2024", size: "1.9MB", sections: 13, key: false },
  ];
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> {ticker}
        </button>
        <h1 className="text-xl font-bold flex-1">SEC Filings — {ticker}</h1>
        <Badge variant="evidence"><CheckCircle size={10} /> EDGAR Verified</Badge>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 space-y-2">
          {filings.map(f => (
            <Card key={f.id} className={cn("p-4 cursor-pointer transition-all", selected === f.id ? "border-primary/50 bg-primary/5" : "hover:border-primary/20")} onClick={() => setSelected(selected === f.id ? null : f.id)}>
              <div className="flex items-start gap-3">
                <div className={cn("px-2 py-0.5 rounded text-xs font-mono font-bold", f.type === "10-K" ? "bg-emerald-500/15 text-emerald-400" : f.type === "10-Q" ? "bg-blue-500/15 text-blue-400" : "bg-orange-500/15 text-orange-400")}>
                  {f.type}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-foreground">{f.period}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{f.date} · {f.sections} sections · {f.size}</div>
                  {f.key && <Badge variant="evidence" className="mt-1 text-xs">Key Filing</Badge>}
                </div>
                <ChevronRight size={14} className="text-muted-foreground shrink-0" />
              </div>
            </Card>
          ))}
        </div>
        <div className="lg:col-span-3">
          {selected ? (
            <Card className="p-5 sticky top-0">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold">Q1 FY2025 10-Q Analysis</h3>
                  <p className="text-xs text-muted-foreground">Filed May 22, 2024 · SEC EDGAR</p>
                </div>
                <Btn variant="secondary" size="sm" icon={<ExternalLink size={12} />}>View on EDGAR</Btn>
              </div>
              <div className="space-y-3">
                {[
                  { section: "Risk Factors", summary: "New risk: export restrictions on H100/H800 chips. China revenue exposure disclosed at ~17% of data center segment.", evidence: 94 },
                  { section: "MD&A — Financial Results", summary: "Revenue grew 262% YoY. Data center segment reached $22.6B, up from $4.3B. Gross margin expansion to 78.4% driven by product mix.", evidence: 97 },
                  { section: "Liquidity & Capital Resources", summary: "$26B in cash and short-term investments. Buyback authorization increased to $25B.", evidence: 96 },
                  { section: "Subsequent Events", summary: "No material subsequent events disclosed after quarter end.", evidence: 91 },
                ].map(s => (
                  <div key={s.section} className="p-3 bg-secondary/30 rounded-lg border border-border/50">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-semibold text-foreground">{s.section}</span>
                      <span className="text-xs font-mono" style={{ color: getEvidenceColor(s.evidence) }}>E:{s.evidence}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{s.summary}</p>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 bg-emerald-500/5 rounded-lg border border-emerald-500/20">
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle size={12} /> XBRL data successfully extracted · 47 tagged financial elements
                </div>
              </div>
            </Card>
          ) : (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              <div className="text-center">
                <FileText size={32} className="mx-auto mb-2 opacity-30" />
                <p>Select a filing to view analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 12: Community Sentiment
// ────────────────────────────────────────────────
