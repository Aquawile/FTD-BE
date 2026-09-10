// ────────────────────────────────────────────────
// COMMUNITY PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, ThumbsUp, MessageSquare } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface CommunityPageProps {
  ticker: string;
  navigate: (p: string) => void;
}

export function CommunityPage({ ticker, navigate }: CommunityPageProps) {
  const [posts, setPosts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker) return;
    let cancelled = false;
    setLoading(true);
    fetch(`/api/tickers/${ticker}/community`)
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setPosts(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, [ticker]);

  const getHypeColor = (h: number) => h > 70 ? "#F59E0B" : h > 40 ? "#F59E0B" : "#EF4444";
  const getEvidenceColor = (e: number) => e > 70 ? "#10B981" : e > 40 ? "#F59E0B" : "#EF4444";

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> {ticker}
        </button>
        <h1 className="text-xl font-bold">Community Sentiment — {ticker}</h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Posts (7d)", value: "8,431", color: "#3B82F6" },
          { label: "Avg Hype Score", value: "79/100", color: "#F59E0B" },
          { label: "Avg Evidence Score", value: "18/100", color: "#10B981" },
          { label: "Net Sentiment", value: "+62%", color: "#8B5CF6" },
        ].map(s => (
          <Card key={s.label} className="p-4 text-center">
            <div className="font-mono font-bold text-xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <div className="space-y-3">
        {loading && (
          Array.from({ length: 5 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
          ))
        ) : error ? (
          <Card className="p-4 text-center text-sm text-red-400">Unable to load community data</Card>
        ) : (
          <div className="space-y-3">
            {posts.map(p => (
              <Card key={p.id} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <Badge variant={p.flair === "DD" || p.flair === "Analysis" ? "default" : p.flair === "Meme" ? "danger" : "neutral"} className="text-xs">{p.flair}</Badge>
                    </div>
                    <h4 className="font-medium text-sm text-foreground mb-2 leading-snug">{p.title}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">{p.message}</p>
                    <div className="flex items-center gap-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1"><ThumbsUp size={10} /> {p.score.toLocaleString()}</span>
                      <span className="flex items-center gap-1"><MessageSquare size={10} /> {p.comments}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <div className="text-xs font-mono" style={{ color: getHypeColor(p.hype) }}>H:{p.hype}</div>
                    <div className="text-xs font-mono" style={{ color: getEvidenceColor(p.evidence) }}>E:{p.evidence}</div>
                    <div className={cn("text-xs font-semibold mt-1", p.evidence < 20 ? "text-red-400" : p.evidence > 60 ? "text-emerald-400" : "text-yellow-400")}>
                      {p.evidence < 20 ? "Low Signal" : p.evidence > 60 ? "High Signal" : "Med Signal"}
                    </div>
                  </div>
                </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const getHypeColor = (h: number) => h > 70 ? "#F59E0B" : h > 40 ? "#F59E0B" : "#EF4444";
const getEvidenceColor = (e: number) => e > 70 ? "#10B981" : e > 40 ? "#F59E0B" : "#EF4444";

export default CommunityPage;