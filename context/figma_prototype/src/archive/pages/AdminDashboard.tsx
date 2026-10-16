import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn } from "../ui";
import { Activity, AlertCircle, ChevronRight, Database, Radio, RefreshCw, Target } from "lucide-react";

function AdminDashboard({ navigate }: { navigate: (p: Page) => void }) {
  const accuracy = 76; // Below 80% threshold
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Admin Operations Portal</h1>
          <p className="text-muted-foreground text-sm mt-0.5">System KPIs · Data pipeline status · Mapping accuracy</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="neutral"><Radio size={9} className="text-emerald-400" /> All systems operational</Badge>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Refresh</Btn>
        </div>
      </div>

      {/* High-priority alert */}
      {accuracy < 80 && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl mb-6">
          <AlertCircle size={18} className="text-red-400 shrink-0" />
          <div className="flex-1">
            <div className="font-semibold text-sm text-red-400">Mapping Accuracy Below Threshold</div>
            <div className="text-xs text-red-400/80">Auto-mapping success rate is {accuracy}% — below the 80% operational minimum. Review queue requires immediate attention.</div>
          </div>
          <Btn variant="danger" size="sm" onClick={() => navigate("admin-mapping")}>Review Queue</Btn>
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Auto-mapping Accuracy", value: `${accuracy}%`, sub: "Target: ≥80%", color: accuracy >= 80 ? "#10B981" : "#EF4444", icon: Target },
          { label: "Articles Ingested (24h)", value: "14,302", sub: "+8.4% vs yesterday", color: "#3B82F6", icon: Database },
          { label: "Queue Pending Review", value: "17", sub: "5 user-reported", color: "#F59E0B", icon: AlertTriangle },
          { label: "Active Users (7d)", value: "1,247", sub: "+12% WoW", color: "#8B5CF6", icon: Users },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs text-muted-foreground mb-1">{s.label}</div>
                <div className="font-mono font-bold text-2xl" style={{ color: s.color }}>{s.value}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{s.sub}</div>
              </div>
              <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${s.color}15` }}>
                <s.icon size={18} style={{ color: s.color }} />
              </div>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline status */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Pipeline Status</h2>
            <button onClick={() => navigate("admin-system")} className="text-xs text-primary hover:underline cursor-pointer">System details →</button>
          </div>
          <Card>
            <div className="divide-y divide-border">
              {[
                { name: "Alpha Vantage News Ingestion", status: "running", last: "2m ago", rate: "142 articles/hr", health: "good" },
                { name: "Reddit Community Scraper", status: "running", last: "5m ago", rate: "803 posts/hr", health: "good" },
                { name: "SEC EDGAR Filing Parser", status: "running", last: "15m ago", rate: "3 filings/hr", health: "good" },
                { name: "RAG Inference Engine", status: "degraded", last: "8m ago", rate: "avg 4.2s latency", health: "warn" },
                { name: "Entity Mapping Worker", status: "running", last: "1m ago", rate: `${accuracy}% accuracy`, health: accuracy >= 80 ? "good" : "error" },
                { name: "Redis Cache Layer", status: "running", last: "0s ago", rate: "94% hit rate", health: "good" },
              ].map(p => (
                <div key={p.name} className="flex items-center gap-3 p-4">
                  <div className={cn("w-2 h-2 rounded-full shrink-0", p.health === "good" ? "bg-emerald-400" : p.health === "warn" ? "bg-yellow-400" : "bg-red-400")} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground">{p.name}</div>
                    <div className="text-xs text-muted-foreground">{p.rate} · Last run: {p.last}</div>
                  </div>
                  <Badge variant={p.health === "good" ? "evidence" : p.health === "warn" ? "hype" : "danger"} className="text-xs capitalize">{p.status}</Badge>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Quick links */}
        <div className="space-y-4">
          <h2 className="font-semibold">Admin Actions</h2>
          <div className="space-y-2">
            {[
              { label: "Mapping Review Queue", desc: "17 items pending", icon: AlertTriangle, page: "admin-mapping" as Page, urgent: true },
              { label: "User Management", desc: "1,247 registered users", icon: Users, page: "admin-users" as Page, urgent: false },
              { label: "System Monitor", desc: "View pipeline details", icon: Activity, page: "admin-system" as Page, urgent: false },
            ].map(a => (
              <Card key={a.label} className={cn("p-4 cursor-pointer hover:border-primary/30 transition-all", a.urgent && "border-red-500/20")} onClick={() => navigate(a.page)}>
                <div className="flex items-center gap-3">
                  <a.icon size={16} className={a.urgent ? "text-red-400" : "text-muted-foreground"} />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{a.label}</div>
                    <div className="text-xs text-muted-foreground">{a.desc}</div>
                  </div>
                  <ChevronRight size={14} className="text-muted-foreground" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 21: Admin Mapping Queue
// ────────────────────────────────────────────────

export default AdminDashboard;
