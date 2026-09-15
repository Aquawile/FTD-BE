import { useState } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn } from "../ui";
import { Activity, AlertTriangle, ArrowRight, Check, FileText } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function AlertsPage({ navigate }: { navigate: (p: Page) => void }) {
  const [filter, setFilter] = useState("all");
  const filtered = filter === "all" ? ALERTS_DATA : filter === "unread" ? ALERTS_DATA.filter(a => !a.read) : ALERTS_DATA.filter(a => a.severity === filter);
  const alertTypeIcon = (type: string) => type === "filing" ? <FileText size={14} /> : type === "narrative_shift" ? <Activity size={14} /> : <AlertTriangle size={14} />;
  const alertTypeColor = (t: string) => t === "filing" ? "#10B981" : t === "narrative_shift" ? "#F59E0B" : "#F97316";

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{ALERTS_DATA.filter(a => !a.read).length} unread notifications</p>
        </div>
        <Btn variant="secondary" size="sm" icon={<Check size={12} />}>Mark all read</Btn>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {["all", "unread", "high", "medium", "low"].map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-lg text-xs border capitalize cursor-pointer transition-all", filter === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}>{f}</button>
        ))}
      </div>
      <div className="space-y-3">
        {filtered.map(a => (
          <Card key={a.id} className={cn("p-4 transition-all cursor-pointer hover:border-primary/30", !a.read && "border-primary/20 bg-primary/3")}>
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${alertTypeColor(a.type)}15` }}>
                <span style={{ color: alertTypeColor(a.type) }}>{alertTypeIcon(a.type)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono font-bold text-sm text-foreground">{a.ticker}</span>
                  <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.severity}</Badge>
                  <Badge variant="neutral" className="text-xs capitalize">{a.type.replace("_", " ")}</Badge>
                  {!a.read && <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block" />}
                </div>
                <p className="text-sm text-foreground">{a.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{a.time}</p>
              </div>
              <Btn variant="ghost" size="sm" onClick={() => navigate("ticker")} icon={<ArrowRight size={12} />}>View</Btn>
            </div>
          </Card>
        ))}
      </div>

      {/* Subscription settings */}
      <Card className="mt-6 p-5">
        <h3 className="font-semibold mb-4">Alert Subscriptions</h3>
        <div className="space-y-3 text-sm">
          {TICKERS.slice(0, 5).map(t => (
            <div key={t.symbol} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
              <div className="flex items-center gap-2">
                <span className="font-mono font-semibold text-xs text-foreground w-12">{t.symbol}</span>
                <span className="text-xs text-muted-foreground">{t.name}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={cn("relative inline-flex w-8 h-5 rounded-full cursor-pointer transition-colors shrink-0", "bg-primary")}>
                  <div className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform translate-x-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 19: Account Settings (Profile)
// ────────────────────────────────────────────────

export default AlertsPage;
