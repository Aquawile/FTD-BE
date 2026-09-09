// ────────────────────────────────────────────────
// TICKER COMPARISON PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, TrendingUp, TrendingDown, ExternalLink, BarChart2 } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface ComparisonPageProps {
  navigate: (p: string) => void;
}

export function ComparisonPage({ navigate }: ComparisonPageProps) {
  const [tickers, setTickers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/tickers/tracked?limit=20")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setTickers(data.slice(0, 3)); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } });
    return () => { /* cancelled = true */ };
  }, []);

  const getHypeColor = (h: number) => h > 70 ? "#F59E0B" : h > 40 ? "#F59E0B" : "#EF4444";
  const getEvidenceColor = (e: number) => e > 70 ? "#10B981" : e > 40 ? "#F59E0B" : "#EF4444";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("dashboard")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> Dashboard
        </button>
        <h1 className="text-xl font-bold flex-1">Multi-Ticker Comparison</h1>
        <Btn variant="secondary" size="sm" icon={<Plus size={12} /}>Add Ticker</Btn>
      </div>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-3"><div className="h-6 bg-secondary rounded w-1/4" /><div className="h-8 bg-secondary rounded w-3/4" /></Card>
          ))}
        )}
      )}

      {error && (
        <div className="text-center py-12 text-red-400">Failed to load comparison data</div>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {tickers.map(t => (
            <div key={t.symbol} className="space-y-4">
              <Card className="p-4 border-t-2" style={{ borderTopColor: t.symbol === "NVDA" ? "#3B82F6" : t.symbol === "TSLA" ? "#F59E0B" : "#8B5CF6" }}>
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
                    <span className="font-mono font-bold text-sm">{t.symbol.slice(0, 2)}</span>
                  </div>
                  <div>
                    <div className="font-mono font-bold text-sm text-foreground">{t.symbol}</div>
                    <div className="text-xs text-muted-foreground">{t.name}</div>
                  </div>
                </Card>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Hype Score</span><span className="font-mono" style={{ color: getHypeColor(t.hype) }}>{t.hype}</span></div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.hype}%`, background: getHypeColor(t.hype) }} /></div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Evidence Score</span><span className="font-mono" style={{ color: getEvidenceColor(t.evidence) }}>{t.evidence}</span></div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.evidence}%`, background: getEvidenceColor(t.evidence) }} /></div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Current Price</span><span className="font-mono font-semibold text-foreground">${t.current_price?.toLocaleString() || "—"}</span></div>
                    <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Change</span><span className={cn("font-mono", t.change > 0 ? "text-emerald-400" : "text-red-400")}>{t.change > 0 ? "+" : ""}{t.change}%</span></div>
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const getHypeColor = (h: number) => h > 70 ? "#F59E0B" : h > 40 ? "#F59E0B" : "#EF4444";
const getEvidenceColor = (e: number) => e > 70 ? "#10B981" : e > 40 ? "#F59E0B" : "#EF4444";

export default ComparisonPage;