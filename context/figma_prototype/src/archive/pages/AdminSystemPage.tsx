import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Card, cn } from "../ui";
import { ChevronLeft, Radio } from "lucide-react";

function AdminSystemPage({ navigate }: { navigate: (p: Page) => void }) {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("admin")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Admin</button>
        <h1 className="text-xl font-bold flex-1">System Monitor</h1>
        <Badge variant="success"><Radio size={9} className="text-emerald-400" /> Live</Badge>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "CPU Usage", value: "34%", color: "#10B981", sub: "4 vCPU · GCP Cloud Run" },
          { label: "Memory", value: "2.1GB", color: "#3B82F6", sub: "of 8GB allocated" },
          { label: "Vector DB Queries/s", value: "124", color: "#8B5CF6", sub: "p95 latency: 42ms" },
          { label: "Cache Hit Rate", value: "94%", color: "#10B981", sub: "Redis Memorystore" },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="font-mono font-bold text-2xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs font-medium text-foreground mb-0.5">{s.label}</div>
            <div className="text-xs text-muted-foreground">{s.sub}</div>
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Pipeline Health</h3>
          <div className="space-y-3">
            {[
              { name: "News Ingestion (Alpha Vantage)", uptime: 99.8, latency: "320ms", status: "healthy" },
              { name: "Reddit Scraper (PRAW)", uptime: 98.2, latency: "180ms", status: "healthy" },
              { name: "SEC EDGAR Parser", uptime: 100.0, latency: "2.1s", status: "healthy" },
              { name: "RAG Inference Engine", uptime: 97.1, latency: "4.2s", status: "degraded" },
              { name: "Hype/Evidence Scorer", uptime: 99.9, latency: "85ms", status: "healthy" },
            ].map(p => (
              <div key={p.name} className="flex items-center gap-3 p-3 bg-secondary/30 rounded-lg">
                <div className={cn("w-2 h-2 rounded-full shrink-0", p.status === "healthy" ? "bg-emerald-400" : "bg-yellow-400")} />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground">{p.name}</div>
                  <div className="text-xs text-muted-foreground">Uptime {p.uptime}% · avg {p.latency}</div>
                </div>
                <Badge variant={p.status === "healthy" ? "evidence" : "hype"} className="text-xs">{p.status}</Badge>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Ingestion Volume (24h)</h3>
          <div className="space-y-3">
            {[
              { source: "Alpha Vantage News", count: 8420, color: "#3B82F6" },
              { source: "Reddit Posts", count: 5102, color: "#F59E0B" },
              { source: "SEC EDGAR Filings", count: 47, color: "#10B981" },
              { source: "Analyst Reports", count: 733, color: "#8B5CF6" },
            ].map(s => (
              <div key={s.source} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{s.source}</span>
                  <span className="font-mono text-foreground">{s.count.toLocaleString()}</span>
                </div>
                <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(s.count / 9000) * 100}%`, background: s.color }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-secondary/30 rounded-lg text-xs text-muted-foreground">
            Total ingested today: <strong className="text-foreground">14,302 items</strong> · Last refresh: 2 minutes ago
          </div>
        </Card>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// MODAL: Error Report
// ────────────────────────────────────────────────

export default AdminSystemPage;
