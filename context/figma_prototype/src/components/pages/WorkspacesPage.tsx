import { useState } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Input, Modal } from "../ui";
import { Briefcase, Hash, MoreVertical, Plus } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function WorkspacesPage({ navigate }: { navigate: (p: Page) => void }) {
  const [showCreate, setShowCreate] = useState(false);
  const [wsName, setWsName] = useState("");

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Workspaces</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Group tickers to track concurrent research themes · Max 50 tickers per workspace</p>
        </div>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>New Workspace</Btn>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {WORKSPACES.map(ws => (
          <Card key={ws.id} className="p-5 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("workspace-detail")}>
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Briefcase size={18} className="text-primary" />
              </div>
              <div className="flex items-center gap-1">
                {ws.alerts > 0 && <Badge variant="hype" className="text-xs">{ws.alerts} alerts</Badge>}
                <button className="p-1 text-muted-foreground hover:text-foreground cursor-pointer" onClick={e => { e.stopPropagation(); navigate("workspace-settings"); }}><MoreVertical size={14} /></button>
              </div>
            </div>
            <h3 className="font-semibold text-foreground mb-1">{ws.name}</h3>
            <p className="text-xs text-muted-foreground mb-4">Created {ws.created} · {ws.tickers.length} tickers</p>
            <div className="flex flex-wrap gap-1.5">
              {ws.tickers.map(t => (
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

      {showCreate && (
        <Modal title="Create New Workspace" onClose={() => setShowCreate(false)}>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Workspace name</label>
              <Input value={wsName} onChange={setWsName} placeholder="e.g., AI Semiconductor Race" icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Add tickers (optional)</label>
              <Input placeholder="NVDA, AMD, TSLA..." icon={<Hash size={14} />} />
              <p className="text-xs text-muted-foreground">Separate with commas. Max 50 tickers.</p>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Btn variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Btn>
              <Btn variant="primary" onClick={() => { setShowCreate(false); navigate("workspace-detail"); }} disabled={!wsName.trim()}>Create Workspace</Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 15: Workspace Detail
// ────────────────────────────────────────────────

export default WorkspacesPage;
