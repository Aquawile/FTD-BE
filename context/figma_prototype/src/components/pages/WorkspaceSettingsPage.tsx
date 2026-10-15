import { useState } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Btn, Card, Input, Modal, cn } from "../ui";
import { Archive, Briefcase, Check, ChevronLeft } from "lucide-react";
import { WorkspaceResponse } from "../../types";

function WorkspaceSettingsPage({ navigate, selectedWorkspace, firebaseUser }: { navigate: (p: Page) => void; selectedWorkspace: WorkspaceResponse | null; firebaseUser: FirebaseUser | null }) {
  const [name, setName] = useState(selectedWorkspace?.name || "");
  const [showDelete, setShowDelete] = useState(false);
  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspace-detail")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back</button>
        <h1 className="text-xl font-bold">Workspace Settings</h1>
      </div>
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
              <textarea autoComplete="off" className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none" rows={3} placeholder="Track concurrent AI chip developments..." />
            </div>
            <Btn variant="primary" size="sm" icon={<Check size={12} />}>Save Changes</Btn>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Alert Preferences</h3>
          <div className="space-y-3 text-sm">
            {[
              { label: "Narrative shift alerts", desc: "Notify when Hype/Evidence delta changes ≥10 points", enabled: true },
              { label: "New SEC filings", desc: "Alert on new 10-K, 10-Q, or 8-K filings", enabled: true },
              { label: "Reddit hype spikes", desc: "Alert when post volume increases >200% in 4 hours", enabled: false },
            ].map(a => (
              <div key={a.label} className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-foreground">{a.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{a.desc}</div>
                </div>
                <div className={cn("relative inline-flex w-10 h-6 rounded-full cursor-pointer transition-colors shrink-0 mt-0.5", a.enabled ? "bg-primary" : "bg-switch-background")}>
                  <div className={cn("absolute top-1 w-4 h-4 rounded-full bg-white transition-transform", a.enabled ? "translate-x-5" : "translate-x-1")} />
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5 border-red-500/20">
          <h3 className="font-semibold mb-2 text-red-400">Danger Zone</h3>
          <p className="text-xs text-muted-foreground mb-4">Soft-deleting archives ticker history but does not permanently remove your research data.</p>
          <Btn variant="secondary" onClick={() => setShowDelete(true)} className="border-red-500/30 text-red-400 hover:bg-red-500/10" icon={<Archive size={12} />}>Archive Workspace</Btn>
        </Card>
      </div>
      {showDelete && (
        <Modal title="Archive Workspace?" onClose={() => setShowDelete(false)} size="sm">
          <p className="text-sm text-muted-foreground mb-4">This will soft-delete the workspace. Your ticker history and research data will be preserved and accessible via the archive for 90 days.</p>
          <div className="flex gap-2 justify-end">
            <Btn variant="secondary" onClick={() => setShowDelete(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={() => navigate("workspaces")} icon={<Archive size={12} />}>Archive</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 17: AI Chat
// ────────────────────────────────────────────────

export default WorkspaceSettingsPage;
