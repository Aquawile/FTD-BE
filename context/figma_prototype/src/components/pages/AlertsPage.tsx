// ────────────────────────────────────────────────
// ALERTS PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, ChevronRight, Bell, Download, FileText, CheckCircle } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface AlertsPageProps {
  navigate: (p: string) => void;
}

export function AlertsPage({ navigate }: AlertsPageProps) {
  const [filter, setFilter] = useState("all");
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/alerts")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setAlerts(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  const filterOptions = ["all", "unread", "high", "medium", "low"] as const;
  const filtered = alerts.filter(a => {
    if (filter === "all") return true;
    if (filter === "unread") return !a.read;
    return a.severity === filter;
  });

  const alertTypeIcon = (type: string) => type === "filing" ? <FileText size={12} /> : type === "narrative_shift" ? <Activity size={12} /> : <AlertTriangle size={12} />;
  const alertTypeColor = (t: string) => t === "filing" ? "#10B981" : t === "narrative_shift" ? "#F59E0B" : "#F97316";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{alerts.filter(a => !a.read).length} unread notifications</p>
        </div>
        <Btn variant="secondary" size="sm" icon={<CheckCircle size={12} />>Mark all read</Btn>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {(["all", "unread", "high", "medium", "low"] as const).map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-lg text-xs border capitalize cursor-pointer transition-all", filter === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}>{f}</button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <Card className="p-3 text-sm text-red-400">Unable to load alerts</Card>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {filtered.map(a => (
            <Card key={a.id} className={cn("p-4 transition-all cursor-pointer hover:border-primary/30", !a.read && "border-primary/20 bg-primary/3")}>
              <div className="flex items-start gap-2">
                <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", a.read ? "bg-secondary" : "bg-orange-400")} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1 mb-0.5">
                    <span className="font-mono font-semibold text-xs text-foreground">{a.ticker ?? ""}</span>
                    <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.type.replace("_", " ")}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{a.message}</p>
                  <div className="text-xs text-muted-foreground/60 mt-1">{a.time}</div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
          ))}
        )}

      {!loading && !error && alerts.length === 0 && (
        <Card className="p-4 text-center text-sm text-muted-foreground">No alerts</Card>
      )}

      {error && (
        <Card className="p-4 text-center text-sm text-red-400">Unable to load alerts</Card>
      )}
    </div>
  );
}

export default AlertsPage;