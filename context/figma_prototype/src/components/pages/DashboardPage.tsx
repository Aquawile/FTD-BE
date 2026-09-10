// ────────────────────────────────────────────────
// Dashboard Page Component
// ────────────────────────────────────────────────

import { useDashboardStats } from "../hooks";
import { Card, Badge, Button as Btn, TrendingUp, TrendingDown, Sparkline } from "./ui";
import { cn } from "./utils";

export function DashboardPage() {
  const { stats, loading, error } = useDashboardStats();

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Articles Analyzed"
          value={stats?.articles_count?.toLocaleString() || 0}
          icon={<FileText size={16} />}
          color="blue"
        />
        <StatCard
          label="Tracked Tickers"
          value={stats?.tickers_count?.toLocaleString() || 0}
          icon={<TrendingUp size={16} />}
          color="green"
        />
        <StatCard
          label="Active Alerts"
          value={stats?.alerts_count?.toLocaleString() || 0}
          icon={<Bell size={16} />}
          color="orange"
        />
        <StatCard
          label="Avg Evidence Score"
          value={stats?.evidence_score !== null ? stats.evidence_score : "—"}
          icon={<Target size={16} />}
          color="purple"
        />
      </div>

      {/* Top Movers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">Top Hype/Evidence Divergence</h2>
          <button className="text-sm text-primary hover:underline">View All →</button>
        </div>
        <div className="space-y-3">
          {/* Top movers will be rendered here with live data */}
          <div className="p-4 bg-secondary/30 rounded-xl border border-border/50 text-center text-muted-foreground">
            Live data loading... (hooks to be connected)
          </div>
        </div>

      {/* My Workspaces */}
      <div className="space-y-4 mt-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold">My Workspaces</h2>
          <button className="text-sm text-primary hover:underline">Manage →</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Workspace cards will render here */}
          <div className="p-4 bg-secondary/30 rounded-xl border border-border/50 text-center text-muted-foreground">
            No workspaces yet. <button className="text-primary hover:underline ml-2">Create one</button>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="space-y-4 mt-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Recent Alerts</h2>
            <button className="text-sm text-primary hover:underline">All Alerts →</button>
          </div>
          <div className="space-y-2">
            <div className="p-4 bg-secondary/30 rounded-xl border border-border/50 text-center text-muted-foreground">
              No alerts yet. <button className="text-primary hover:underline ml-2">View All</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: React.ReactNode; color: string }) {
  const colors = {
    blue: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    green: "bg-emerald-500/10 text-emerald-500 border-emerald-500/20",
    orange: "bg-orange-500/10 text-orange-500 border-orange-500/20",
    purple: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  };
  return (
    <div className={`p-4 rounded-xl border ${colors[color as keyof typeof colors] || "bg-secondary/30 border-border"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground uppercase">{color}</span>
      </div>
      <div className="flex items-center justify-between">
        <span className="font-mono text-2xl font-bold text-foreground">{value}</span>
        <div className={`p-2 rounded-lg ${colors[color as keyof typeof colors] || "bg-secondary/30"}`}>
          {icon}
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;