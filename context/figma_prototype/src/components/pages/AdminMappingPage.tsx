// ────────────────────────────────────────────────
// ADMIN MAPPING PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, Search, Filter, MoreHorizontal, Edit2, Trash2, Plus, Download, Eye, RefreshCw, CheckCircle, XCircle, AlertTriangle, Clock } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface AdminMappingPageProps {
  navigate: (p: string) => void;
}

export function AdminMappingPage({ navigate }: AdminMappingPageProps) {
  const [queue, setQueue] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/admin/mapping-queue")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setQueue(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  const filtered = queue.filter(q => {
    if (filter !== "all" && q.type !== filter) return false;
    if (search && !q.article.toLowerCase().includes(search.toLowerCase()) && !q.mapped.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Mapping Queue</h1>
          <p className="text-muted-foreground text-sm mt-1">Review and verify article-ticker mappings</p>
        </div>
        <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />>Refresh</Btn>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {["all", "Wrong Ticker", "Ambiguous", "Verify"].map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-lg text-xs border capitalize cursor-pointer transition-all", filter === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}>{f}</button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search articles..." className="w-64 pl-9 pr-3 py-2 bg-input-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50" />
          </div>
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <Card className="p-4 text-center text-sm text-red-400">Unable to load mapping queue</Card>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          {queue.filter(q => {
            if (filter !== "all" && q.type !== filter) return false;
            if (search && !q.article.toLowerCase().includes(search.toLowerCase()) && !q.mapped.toLowerCase().includes(search.toLowerCase())) return false;
            return true;
          }).map(q => (
            <Card key={q.id} className="p-4 hover:border-primary/30 transition-all">
              <div className="flex items-start gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-2">
                    <Badge variant={q.type === "Wrong Ticker" ? "danger" : q.type === "Ambiguous" ? "hype" : "neutral"} className="text-xs">{q.type}</Badge>
                    <Badge variant="neutral" className="text-xs">{q.source}</Badge>
                    <Badge variant="neutral" className="text-xs">{Math.round(q.confidence * 100)}% confidence</Badge>
                    <span className="text-xs text-muted-foreground">{q.time}</span>
                    <Badge variant={q.reporter === "user" ? "default" : "hype"} className="text-xs">{q.reporter}</Badge>
                  </div>
                  <div className="mt-2">
                    <p className="font-medium text-sm text-foreground truncate">{q.article}</p>
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-sm">
                    <span className="font-mono text-xs text-foreground">{q.mapped}</span>
                    <Badge variant={q.suggested === q.mapped ? "evidence" : "hype"} className="text-xs">Suggested: {q.suggested}</Badge>
                    <Badge variant="hype" className="text-xs">{Math.round(q.confidence * 100)}% confidence</Badge>
                    <Badge variant="neutral" className="text-xs">{q.reporter}</Badge>
                    <span className="text-xs text-muted-foreground">{q.time}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-auto shrink-0">
                  <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors cursor-pointer" title="View"><Eye size={12} /></button>
                  <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors cursor-pointer" title="Edit"><Edit2 size={12} /></button>
                  <button className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer" title="Delete"><Trash2 size={12} /></button>
                  <button className="p-1.5 text-muted-foreground hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors cursor-pointer" title="Approve"><CheckCircle size={12} className="text-emerald-400" /></button>
                  <button className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer" title="Reject"><XCircle size={12} className="text-red-400" /></button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default AdminMappingPage;