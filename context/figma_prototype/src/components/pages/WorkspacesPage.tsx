import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Input, Modal } from "../ui";
import { Briefcase, MoreVertical, Plus, Trash2 } from "lucide-react";
import { fetchWorkspaces, fetchCreateWorkspace, fetchDeleteWorkspace } from "../../api";
import { WorkspaceResponse } from "../../types";

function WorkspacesPage({ navigate, firebaseUser, setSelectedWorkspace }: { navigate: (p: Page) => void; firebaseUser: FirebaseUser | null; setSelectedWorkspace: (ws: any) => void }) {
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [wsName, setWsName] = useState("");

  useEffect(() => {
    let cancelled = false;
    const loadWorkspaces = async () => {
      if (!firebaseUser) {
        setWorkspaces([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      try {
        const data = await fetchWorkspaces(firebaseUser);
        if (!cancelled) setWorkspaces(data);
      } catch {
        if (!cancelled) setWorkspaces([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    loadWorkspaces();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const handleCreate = async () => {
    if (!wsName.trim() || !firebaseUser) return;
    try {
      const newWs = await fetchCreateWorkspace(wsName.trim(), [], firebaseUser);
      setWorkspaces([newWs, ...workspaces]);
    } catch {
      // error handling
    }
    setShowCreate(false);
    setWsName("");
  };

  const handleDelete = async (id: number) => {
    if (!firebaseUser) return;
    try {
      await fetchDeleteWorkspace(id, firebaseUser);
      setWorkspaces(workspaces.filter(ws => ws.id !== id));
    } catch {
      // error handling
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Workspaces</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Group tickers to track concurrent research themes · Max 50 tickers per workspace</p>
        </div>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>New Workspace</Btn>
      </div>

      {loading ? (
        <div className="text-center py-12 text-muted-foreground">Loading workspaces...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {workspaces.map(ws => (
            <Card key={ws.id} className="p-5 cursor-pointer hover:border-primary/30 transition-all" onClick={() => { setSelectedWorkspace(ws); navigate("workspace-detail"); }}>
              <div className="flex items-start justify-between mb-4">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                  <Briefcase size={18} className="text-primary" />
                </div>
                <div className="flex items-center gap-1">
                  <button
                    className="p-1 text-muted-foreground hover:text-red-400 cursor-pointer"
                    onClick={e => { e.stopPropagation(); handleDelete(ws.id); }}
                  >
                    <Trash2 size={14} />
                  </button>
                  <button className="p-1 text-muted-foreground hover:text-foreground cursor-pointer" onClick={e => { e.stopPropagation(); navigate("workspace-settings"); }}><MoreVertical size={14} /></button>
                </div>
              </div>
              <h3 className="font-semibold text-foreground mb-1">{ws.name}</h3>
              <p className="text-xs text-muted-foreground mb-4">Created {ws.created_at || "—"} · {ws.tickers.length} tickers</p>
              <div className="flex flex-wrap gap-1.5">
                {ws.tickers.map(t => (
                  <span key={t} className="px-2 py-0.5 bg-secondary rounded-md text-xs font-mono text-muted-foreground border border-border">{t}</span>
                ))}
              </div>
            </Card>
          ))}
          <button onClick={() => setShowCreate(true)} className="flex flex-col items-center justify-center p-5 rounded-xl border-2 border-dashed border-border hover:border-primary/40 hover:bg-secondary/20 cursor-pointer transition-all min-h-[160px]">
            <Plus size={24} className="text-muted-foreground mb-2" />
            <span className="text-sm text-muted-foreground">Create workspace</span>
          </button>
        </div>
      )}

      {workspaces.length === 0 && !loading && (
        <div className="text-center py-12">
          <Briefcase size={48} className="text-muted-foreground/30 mx-auto mb-3" />
          <p className="text-muted-foreground mb-4">No workspaces yet. Create one to get started.</p>
          <Btn variant="primary" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>Create Your First Workspace</Btn>
        </div>
      )}

      {showCreate && (
        <Modal title="Create New Workspace" onClose={() => setShowCreate(false)}>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Workspace name</label>
              <Input value={wsName} onChange={setWsName} placeholder="e.g., My Research Theme" icon={<Briefcase size={14} />} />
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Btn variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Btn>
              <Btn variant="primary" onClick={handleCreate} disabled={!wsName.trim()}>Create Workspace</Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default WorkspacesPage;
