// ────────────────────────────────────────────────
// REPORT MODAL
// ────────────────────────────────────────────────

import { useState } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, Search, Filter, MoreHorizontal, Edit2, Trash2, Plus, Download, Eye, RefreshCw, CheckCircle, XCircle, AlertTriangle, Clock, Send, Info } from "./ui";
import { cn } from "../utils";
import { Modal } from "./ui";

interface ReportModalProps {
  onClose: () => void;
}

export function ReportModal({ onClose }: ReportModalProps) {
  const [reason, setReason] = useState("wrong-ticker");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <Modal title="Report Submitted" onClose={onClose} size="sm">
        <div className="text-center space-y-4 py-4">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
            <CheckCircle size={28} className="text-emerald-400" />
          </div>
          <div>
            <h3 className="font-semibold mb-1">Feedback received</h3>
            <p className="text-sm text-muted-foreground">Your report has been added to the admin review queue. No changes were made to the live view for other users.</p>
          </div>
          <Badge variant="neutral"><Info size={10} /> Queue position #18 · Est. review: 4 hours</Badge>
          <Btn variant="primary" className="w-full justify-center" onClick={onClose}>Close</Btn>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Report Mapping Error" onClose={onClose}>
      <div className="space-y-4">
        <div className="p-3 bg-secondary/50 rounded-lg border border-border text-xs text-muted-foreground">
          <strong className="text-foreground">Flagged:</strong> "Analysts Predict NVDA Will Reach $1,200 on Insatiable AI Demand" — Seeking Alpha
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Reason for report</label>
          <select value={reason} onChange={e => setReason(e.target.value)} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50">
            <option value="wrong-ticker">Wrong ticker mapping</option>
            <option value="wrong-source">Incorrect source attribution</option>
            <option value="false-claim">False or misleading claim extracted</option>
            <option value="duplicate">Duplicate article</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Additional context (optional)</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={3}
            placeholder="Describe the issue in more detail..."
            className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
          />
        </div>
        <p className="text-xs text-muted-foreground">Submitting will add this to the admin review queue. The article will remain visible to all users until a review decision is made.</p>
        <div className="flex gap-2 justify-end">
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" onClick={() => setSubmitted(true)} icon={<Send size={12} /}>Send Report</Btn>
        </div>
      </div>
    </Modal>
  );
}

export default ReportModal;