import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Sparkline, cn } from "../ui";
import { FileText, MessageSquare, Sparkles, Target, TrendingDown, TrendingUp } from "lucide-react";
import { fetchWorkspaces, getTrackedTickers, getAlerts } from "../../api";
import { WorkspaceResponse, AlertResponse, TrackedTicker } from "../../types";

function DashboardPage({ navigate, setSelectedTicker, firebaseUser }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; firebaseUser: FirebaseUser | null }) {
  const [stats, setStats] = useState<{ articles_count: number; tickers_count: number; alerts_count: number; evidence_score: number | null; vectorized_sec_count: number } | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [wsLoading, setWsLoading] = useState(true);
  const [alerts, setAlerts] = useState<AlertResponse[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(true);
  const [trackedTickers, setTrackedTickers] = useState<TrackedTicker[]>([]);
  const [tickersLoading, setTickersLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetchStats = async () => {
      try {
        const res = await fetch("/api/dashboard/stats");
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) { setStats(data); setStatsLoading(false); }
      } catch {
        if (!cancelled) { setStatsError(true); setStatsLoading(false); }
      }
    };
    fetchStats();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchAlerts = async () => {
      try {
        const data = await getAlerts(3);
        if (!cancelled) setAlerts(data);
      } catch {
        if (!cancelled) setAlerts([]);
      } finally {
        if (!cancelled) setAlertsLoading(false);
      }
    };
    fetchAlerts();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const fetchTickers = async () => {
      setTickersLoading(true);
      try {
        const data = await getTrackedTickers(50);
        if (!cancelled) setTrackedTickers(data);
      } catch {
        if (!cancelled) setTrackedTickers([]);
      } finally {
        if (!cancelled) setTickersLoading(false);
      }
    };
    fetchTickers();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!firebaseUser) {
      setWorkspaces([]);
      setWsLoading(false);
      return;
    }
    let cancelled = false;
    const loadWorkspaces = async () => {
      setWsLoading(true);
      try {
        const data = await fetchWorkspaces(firebaseUser);
        if (!cancelled) setWorkspaces(data);
      } catch {
        if (!cancelled) setWorkspaces([]);
      } finally {
        if (!cancelled) setWsLoading(false);
      }
    };
    loadWorkspaces();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const formatCount = (n: number) => {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  };

  const topMovers = trackedTickers.slice(0, 5);
  const spData = [45, 52, 48, 63, 71, 68, 74, 69, 77, 82, 79, 84];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Good morning 👋</h1>
        </div>
        <Btn variant="primary" onClick={() => navigate("chat")} icon={<MessageSquare size={14} />}>Ask AI</Btn>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 2 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-6 bg-secondary rounded w-1/3" /></div></Card>
          ))
        ) : statsError ? (
          <Card className="p-4 col-span-full text-sm text-red-400">Unable to load dashboard stats</Card>
        ) : (
          <>
            <Card className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-muted-foreground text-xs mb-1">Articles Analyzed</div>
                  <div className="font-mono font-bold text-2xl text-foreground">{formatCount(stats?.articles_count ?? 0)}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Total in database</div>
                </div>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-emerald-500/10 text-emerald-400"><FileText size={18} /></div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-muted-foreground text-xs mb-1">Tickers Tracked</div>
                  <div className="font-mono font-bold text-2xl text-foreground">{formatCount(stats?.tickers_count ?? 0)}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Across all sources</div>
                </div>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-blue-500/10 text-blue-400"><Target size={18} /></div>
              </div>
            </Card>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Movers */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-foreground">Top Hype/Evidence Divergence</h2>
            <button onClick={() => navigate("search")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
          </div>
          <Card>
            <div className="divide-y divide-border">
              {tickersLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 p-4">
                    <div className="w-10 h-10 rounded-xl bg-secondary animate-pulse shrink-0" />
                    <div className="flex-1 space-y-1"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-1/3" /></div>
                    <div className="w-12 h-3 bg-secondary rounded animate-pulse shrink-0" />
                  </div>
                ))
              ) : topMovers.map(t => {
                const changePct = (typeof t.change_percent === "number" ? t.change_percent : 0) || 0;
                const price = t.current_price ?? 0;
                return (
                <div
                  key={t.symbol}
                  className="flex items-center gap-4 p-4 hover:bg-secondary/30 cursor-pointer transition-all"
                  onClick={() => { setSelectedTicker(t.symbol); navigate("ticker"); }}
                >
                  <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center shrink-0">
                    <span className="font-mono font-bold text-xs text-foreground">{t.symbol.slice(0, 2)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-semibold text-sm text-foreground">{t.symbol}</span>
                      <span className="text-muted-foreground text-xs truncate">{t.name || t.symbol}</span>
                    </div>
                    <div className="mt-1.5 flex items-center gap-3">
                      <div className="text-xs text-muted-foreground">
                        Evidence: {t.evidence_score ?? "—"} | Hype: {t.hype_score ?? "—"}
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="font-mono text-sm font-semibold text-foreground">${price.toLocaleString()}</div>
                    <div className={cn("text-xs flex items-center gap-0.5 justify-end", changePct > 0 ? "text-emerald-400" : "text-red-400")}>
                      {changePct > 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {changePct > 0 ? "+" : ""}{changePct}%
                    </div>
                  </div>
                  <Sparkline data={spData.map(v => v + Math.random() * 8 - 4)} color={changePct > 0 ? "#10B981" : "#EF4444"} />
                </div>
                );
              })}
            </div>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Recent alerts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-foreground">Recent Alerts</h2>
              <button onClick={() => navigate("alerts")} className="text-xs text-primary hover:underline cursor-pointer">All alerts →</button>
            </div>
            <div className="space-y-2">
              {alertsLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i} className="p-3"><div className="animate-pulse space-y-1"><div className="h-2.5 bg-secondary rounded w-3/4" /><div className="h-2.5 bg-secondary rounded w-1/2" /></div></Card>
                ))
              ) : alerts.map(a => (
                <Card key={a.id} className="p-3">
                  <div className="flex items-start gap-2">
                    <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", a.read ? "bg-secondary" : "bg-orange-400")} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 mb-0.5">
                        <span className="font-mono font-semibold text-xs text-foreground">{a.ticker || "—"}</span>
                        <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.type.replace("_", " ")}</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">{a.message}</p>
                      <div className="text-xs text-muted-foreground/60 mt-1">{a.time || "—"}</div>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </div>

          {/* Workspace quick view */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-foreground">My Workspaces</h2>
              <button onClick={() => navigate("workspaces")} className="text-xs text-primary hover:underline cursor-pointer">Manage →</button>
            </div>
            <div className="space-y-2">
              {wsLoading ? (
                <div className="text-center py-4 text-muted-foreground text-xs">Loading workspaces...</div>
              ) : workspaces.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground text-xs">No workspaces yet. Create one to get started.</div>
              ) : (
                workspaces.slice(0, 3).map(ws => (
                  <Card key={ws.id} className="p-3 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("workspace-detail")}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-sm text-foreground">{ws.name}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{ws.tickers.join(", ")}</div>
                      </div>
                      {ws.alerts > 0 && <Badge variant="hype" className="text-xs">{ws.alerts}</Badge>}
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI chat preview */}
      <Card className="p-5 border-primary/20 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
            <Sparkles size={18} className="text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-foreground">AI Research Assistant</h3>
            <p className="text-xs text-muted-foreground">Ask complex multi-ticker questions. Sources always cited.</p>
          </div>
          <Btn variant="primary" size="sm" onClick={() => navigate("chat")} icon={<MessageSquare size={12} />}>Open Chat</Btn>
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 8: Search Results
// ────────────────────────────────────────────────

export default DashboardPage;
