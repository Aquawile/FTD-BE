// ────────────────────────────────────────────────
// WORKSPACE DETAIL PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, Plus, Briefcase, Hash, MoreVertical, ChevronRight, Bell, Trash2, Edit2 } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface WorkspaceDetailPageProps {
  navigate: (p: string) => void;
}

export function WorkspaceDetailPage({ navigate }: WorkspaceDetailPageProps) {
  const [workspace, setWorkspace] = useState<any>(null);
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/workspaces/1") // TODO: use workspace ID from URL
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setWorkspace(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-muted-foreground">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to load workspace</p>
        </div>
      )}

      {!loading && !error && workspace && (
        <div>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <button onClick={() => navigate("workspaces")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
                <ChevronLeft size={14} /> Workspaces
              </button>
              <div>
                <h1 className="text-2xl font-bold">{workspace.name}</h1>
                <p className="text-muted-foreground text-sm mt-1">{workspace.tickers?.length || 0} tickers · {workspace.alerts || 0} alerts</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Btn variant="secondary" size="sm" icon={<Plus size={12} />}>Add Ticker</Btn>
              <Btn variant="secondary" size="sm" icon={<MoreVertical size={12} />} onClick={() => navigate("workspace-settings")}>Settings</Btn>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
            {/* Ticker list */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-foreground">Tracked Tickers</h2>
                <Btn variant="secondary" size="sm" icon={<Plus size={12} />}>Add Ticker</Btn>
              </div>
              <div className="space-y-3">
                {["NVDA", "AMD", "INTC", "TSM", "TSLA", "NIO"].map(t => (
                  <Card key={t} className="p-4 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("ticker")}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center shrink-0">
                          <span className="font-mono font-bold text-xs text-foreground">{t.slice(0, 2)}</span>
                        </div>
                        <div>
                          <div className="font-medium text-sm text-foreground">{t}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">{t === "NVDA" ? "Semiconductors" : t === "TSLA" ? "Automotive / EV" : t === "AMD" ? "Semiconductors" : "Technology"}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="hype" className="text-xs">H: 84</Badge>
                        <Badge variant="evidence" className="text-xs">E: 71</Badge>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            </div>

            {/* Alerts & Quick Actions */}
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-semibold text-foreground">Recent Alerts</h2>
                  <Btn variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>View All</Btn>
                </div>
                <div className="space-y-2">
                  {[
                    { ticker: "NVDA", type: "narrative_shift", message: "Hype/Evidence score delta exceeded +10 threshold", time: "2h ago", read: false, severity: "high" },
                    { ticker: "TSLA", type: "filing", message: "New SEC 8-K filing detected — executive compensation update", time: "5h ago", read: false, severity: "medium" },
                    { ticker: "AMD", type: "narrative_shift", message: "Community sentiment reversed — net negative shift detected", time: "1d ago", read: true, severity: "medium" },
                  ].map(a => (
                    <Card key={a.ticker + a.time} className="p-4">
                      <div className="flex items-start gap-2">
                        <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", a.read ? "bg-secondary" : "bg-orange-400")} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1 mb-0.5">
                            <span className="font-mono font-semibold text-xs text-foreground">{a.ticker}</span>
                            <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.type.replace("_", " ")}</Badge>
                          </div>
                          <p className="text-xs text-muted-foreground leading-relaxed">{a.message}</p>
                          <div className="text-xs text-muted-foreground/60 mt-1">{a.time}</div>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              {/* Quick Actions */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                <div className="space-y-2">
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Clock size={12} />} onClick={() => navigate("ticker-timeline")}>View Timeline</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<FileText size={12} />} onClick={() => navigate("ticker-filings")}>SEC Filings</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Users size={12} />} onClick={() => navigate("ticker-community")}>Community Sentiment</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-timeline")}>Export Report</Btn>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkspaceDetailPage;