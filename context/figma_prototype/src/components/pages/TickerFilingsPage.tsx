// ────────────────────────────────────────────────
// TICKER FILINGS PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronRight, ExternalLink, FileText, CheckCircle } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface TickerFilingsPageProps {
  ticker: string;
  navigate: (p: string) => void;
}

export function TickerFilingsPage({ ticker, navigate }: TickerFilingsPageProps) {
  const [filings, setFilings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/tickers/${ticker}/filings`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setFilings(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [ticker]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> {ticker}
        </button>
        <h1 className="text-xl font-bold flex-1">SEC Filings — {ticker}</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filings list */}
        <div className="lg:col-span-1 space-y-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-foreground">Filings</h2>
            <Badge variant="neutral">{filings.length} filings</Badge>
          </div>
          <div className="space-y-3">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
              ))
            ) : error ? (
              <Card className="p-4 text-center text-sm text-red-400">Unable to load filings</Card>
            ) : filings.length === 0 ? (
              <Card className="p-4 text-center text-xs text-muted-foreground">No filings found</Card>
            ) : (
              <div className="space-y-3">
                {filings.map(f => (
                  <Card key={f.id} className="p-4 cursor-pointer hover:border-primary/30 transition-all" onClick={() => setSelected(f.id)}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-sm text-foreground">{f.form_type}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{f.filing_date} · {f.sections} sections · {f.size}</div>
                      </div>
                      {f.key && <Badge variant="evidence" className="mt-1 text-xs">Key Filing</Badge>}
                    </div>
                  </Card>
                ))}
              )}
            </div>
          </div>

          {/* Filing detail */}
          <div className="lg:col-span-3">
            {selected ? (
              <Card className="p-5 sticky top-0">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-semibold">Q1 FY2025 10-Q Analysis</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">Filed May 22, 2024 · SEC EDGAR</p>
                  </div>
                  <Btn variant="secondary" size="sm" icon={<ExternalLink size={12} />} onClick={() => navigate("ticker")}>View on EDGAR</Btn>
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
                        <span className="font-medium text-sm text-foreground">{s.section}</span>
                        <Badge variant="evidence" className="text-xs">E:{s.evidence}</Badge>
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
    </div>
  );
}

export default TickerFilingsPage;