import { useEffect, useState } from "react";
import type { User as FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Btn, Card, Input, Modal, cn } from "../ui";
import { Archive, Briefcase, Check, ChevronLeft } from "lucide-react";
import { WorkspaceResponse } from "../../types";
import { fetchDeleteWorkspace, fetchUpdateWorkspace } from "../../api";

function WorkspaceSettingsPage({ navigate, selectedWorkspace, firebaseUser, onSaved, onArchived }: {
  navigate: (p: Page) => void;
  selectedWorkspace: WorkspaceResponse | null;
  firebaseUser: FirebaseUser | null;
  onSaved: (ws: WorkspaceResponse) => void;
  onArchived: () => void;
}) {
  const ws = selectedWorkspace;
  const [name, setName] = useState(ws?.name || "");
  const [description, setDescription] = useState(ws?.description || "");
  const [alertOnFilings, setAlertOnFilings] = useState(!!ws?.alert_on_filings);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showArchive, setShowArchive] = useState(false);
  const [archiving, setArchiving] = useState(false);

  useEffect(() => {
    setName(ws?.name || "");
    setDescription(ws?.description || "");
    setAlertOnFilings(!!ws?.alert_on_filings);
  }, [ws?.id]);

  if (!ws) {
    return (
      <div className="p-6 max-w-2xl mx-auto space-y-4">
        <p className="text-sm text-muted-foreground">Choose a workspace first.</p>
        <Btn variant="secondary" onClick={() => navigate("workspaces")}>Go to Workspaces</Btn>
      </div>
    );
  }

  const dirty = name.trim() !== ws.name || description !== (ws.description || "");

  const save = async () => {
    if (!name.trim()) { setError("Workspace name can't be empty."); return; }
    setSaving(true); setError(null);
    try {
      onSaved(await fetchUpdateWorkspace(ws.id, { name: name.trim(), description }, firebaseUser));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      setError(e.message || "Couldn't save changes.");
    } finally {
      setSaving(false);
    }
  };

  // Saved immediately: turning it on keeps a "new SEC filing" alert on for every ticker in
  // this workspace (and tickers added later); turning it off pauses those alerts.
  const toggleFilingAlerts = async () => {
    const next = !alertOnFilings;
    setAlertOnFilings(next); setError(null);
    try {
      onSaved(await fetchUpdateWorkspace(ws.id, { alert_on_filings: next }, firebaseUser));
    } catch (e: any) {
      setAlertOnFilings(!next);
      setError(e.message || "Couldn't update alerts.");
    }
  };

  const archive = async () => {
    setArchiving(true); setError(null);
    try {
      await fetchDeleteWorkspace(ws.id, firebaseUser);
      setShowArchive(false);
      onArchived();
    } catch (e: any) {
      setError(e.message || "Couldn't archive the workspace.");
      setArchiving(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspace-detail")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back</button>
        <span className="text-muted-foreground">/</span>
        <h1 className="text-lg font-bold">{ws.name} · Settings</h1>
      </div>
      {error && <p className="text-sm text-red-400 mb-4">{error}</p>}
      <div className="space-y-5">
        <Card className="p-5">
          <h3 className="font-semibold mb-4">General</h3>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Workspace name</label>
              <Input value={name} onChange={setName} icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Description (optional)</label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                maxLength={1000}
                rows={3}
                placeholder="What this workspace is tracking"
                className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
              />
            </div>
            <Btn variant="primary" size="sm" icon={<Check size={12} />} onClick={save} disabled={saving || !dirty}>
              {saved ? "Saved" : saving ? "Saving…" : "Save Changes"}
            </Btn>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Alert Preferences</h3>
          <div className="flex items-start justify-between gap-4 text-sm">
            <div>
              <div className="font-medium text-foreground">New SEC filings</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                Alert me when any ticker in this workspace files a new 8-K or 10-K. Checked after each nightly data sync.
              </div>
            </div>
            <button
              type="button" role="switch" aria-checked={alertOnFilings} aria-label="Alert on new SEC filings"
              onClick={toggleFilingAlerts}
              className={cn("relative inline-flex w-10 h-6 rounded-full cursor-pointer transition-colors shrink-0 mt-0.5", alertOnFilings ? "bg-primary" : "bg-switch-background")}
            >
              <span className={cn("absolute top-1 w-4 h-4 rounded-full bg-white transition-transform", alertOnFilings ? "translate-x-5" : "translate-x-1")} />
            </button>
          </div>
        </Card>
        <Card className="p-5 border-red-500/20">
          <h3 className="font-semibold mb-2 text-red-400">Archive</h3>
          <p className="text-sm text-muted-foreground mb-4">Archiving hides this workspace from your list. Its tickers and history are kept.</p>
          <Btn variant="secondary" onClick={() => setShowArchive(true)} className="border-red-500/30 text-red-400 hover:bg-red-500/10" icon={<Archive size={12} />}>Archive Workspace</Btn>
        </Card>
      </div>
      {showArchive && (
        <Modal title="Archive workspace?" onClose={() => setShowArchive(false)}>
          <p className="text-sm text-muted-foreground mb-4">"{ws.name}" will be hidden from your workspaces. Nothing is deleted.</p>
          <div className="flex gap-2 justify-end">
            <Btn variant="secondary" onClick={() => setShowArchive(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={archive} disabled={archiving} icon={<Archive size={12} />}>{archiving ? "Archiving…" : "Archive"}</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default WorkspaceSettingsPage;
