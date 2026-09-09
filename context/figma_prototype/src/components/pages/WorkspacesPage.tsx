// ────────────────────────────────────────────────
// WORKSPACES PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, Plus, Briefcase, Hash, MoreVertical, ChevronRight, Bell, Trash2, Edit2 } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface WorkspacesPageProps {
  navigate: (p: string) => void;
}

export function WorkspacesPage({ navigate }: WorkspacesPageProps) {
  const [showCreate, setShowCreate] = useState(false);
  const [wsName, setWsName] = useState("");
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/workspaces")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setWorkspaces(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Workspaces</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Group tickers to track concurrent research themes · Max 50 tickers per workspace</p>
        </div>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>New Workspace</Btn>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <Card className="p-4 text-center text-sm text-red-400">Unable to load workspaces</Card>
      )}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {workspaces.map(ws => (
            <Card key={ws.id} className="p-5 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("workspace-detail")}>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Briefcase size={18} className="text-primary" />
                </div>
                <div className="flex items-center gap-1">
                  {ws.alerts > 0 && <Badge variant="hype" className="text-xs">{ws.alerts} alerts</Badge>}
                  <button className="p-1 text-muted-foreground hover:text-foreground cursor-pointer" onClick={e => { e.stopPropagation(); navigate("workspace-settings"); }}><MoreVertical size={14} /></button>
                </div>
              </div>
              <h3 className="font-medium text-sm text-foreground mb-1">{ws.name}</h3>
              <div className="text-xs text-muted-foreground mt-2">Created {ws.created_at ? new Date(ws.created_at).toLocaleDateString() : "—"} · {ws.tickers?.length || 0} tickers</div>
              <div className="flex flex-wrap gap-1.5 mt-2">
                {ws.tickers?.map(t => (
                  <span key={t} className="px-2 py-0.5 bg-secondary rounded-md text-xs font-mono text-muted-foreground border border-border">{t}</span>
                ))}
              </div>
            </Card>
          ))}
          {/* Add card */}
          <button onClick={() => setShowCreate(true)} className="flex flex-col items-center justify-center p-5 rounded-xl border-2 border-dashed border-border hover:border-primary/40 hover:bg-secondary/20 cursor-pointer transition-all min-h-[160px]">
            <Plus size={24} className="text-muted-foreground mb-2" />
            <span className="text-sm text-muted-foreground">Create workspace</span>
          </button>
        </div>
      )}

      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-lg">Create Workspace</h3>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground"><X size={20} /></button>
            </div>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Workspace name</label>
                <Input value={wsName} onChange={setWsName} placeholder="e.g., AI Semiconductor Race" icon={<Briefcase size={14} />} />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium">Add tickers (optional)</label>
                <Input placeholder="NVDA, AMD, INTC, TSM..." icon={<Hash size={14} />} />
                <p className="text-xs text-muted-foreground">Separate with commas. Max 50 tickers.</p>
              </div>
              <div className="flex gap-2 justify-end pt-2">
                <Btn variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Btn>
                <Btn variant="primary" onClick={() => { setShowCreate(false); navigate("workspace-detail"); }} disabled={!wsName.trim()}>Create Workspace</Btn>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkspacesPage;