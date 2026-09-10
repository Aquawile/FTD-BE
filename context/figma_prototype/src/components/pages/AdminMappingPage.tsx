import { useState } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn } from "../ui";
import { AlertTriangle, Archive, Check, CheckCircle, ChevronLeft, Filter, RefreshCw } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function AdminMappingPage({ navigate }: { navigate: (p: Page) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [items, setItems] = useState(MAPPING_QUEUE);
  const [actionModal, setActionModal] = useState<{ id: string; action: string } | null>(null);

  const resolve = (id: string, action: string) => {
    setItems(prev => prev.filter(i => i.id !== id));
    setActionModal(null);
    setSelected(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("admin")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Admin</button>
        <h1 className="text-xl font-bold flex-1">Mapping Review Queue</h1>
        <Badge variant="danger">{items.length} pending</Badge>
        <Btn variant="secondary" size="sm" icon={<Filter size={12} />}>Filter</Btn>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Queue list */}
        <div className="lg:col-span-3 space-y-2">
          {items.map(item => (
            <Card key={item.id} className={cn("p-4 cursor-pointer transition-all hover:border-primary/20", selected === item.id && "border-primary/50 bg-primary/5")} onClick={() => setSelected(item.id)}>
              <div className="flex items-start gap-3">
                <div className={cn("px-1.5 py-0.5 rounded text-xs font-mono font-bold shrink-0", item.reporter === "user" ? "bg-orange-500/15 text-orange-400" : "bg-blue-500/15 text-blue-400")}>
                  {item.reporter === "user" ? "USR" : "AUTO"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground leading-snug mb-1 truncate">{item.article}</div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{item.source}</span>
                    <span>·</span>
                    <span>Mapped: <strong className="text-foreground">{item.mapped}</strong></span>
                    <span>→ Suggested: <strong className="text-primary">{item.suggested}</strong></span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={item.confidence < 0.5 ? "danger" : item.confidence < 0.7 ? "hype" : "evidence"} className="text-xs">
                      {Math.round(item.confidence * 100)}% confidence
                    </Badge>
                    <Badge variant="neutral" className="text-xs">{item.type}</Badge>
                    <span className="text-xs text-muted-foreground">{item.time}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
          {items.length === 0 && (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              <div className="text-center">
                <CheckCircle size={24} className="mx-auto mb-2 text-emerald-400" />
                Queue is clear
              </div>
            </div>
          )}
        </div>

        {/* Review panel */}
        <div className="lg:col-span-2">
          {selected ? (() => {
            const item = items.find(i => i.id === selected)!;
            if (!item) return null;
            return (
              <Card className="p-5 sticky top-0">
                <h3 className="font-semibold mb-4">Review Record</h3>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-secondary/50 rounded-lg">
                    <div className="text-xs text-muted-foreground mb-1">Article</div>
                    <div className="font-medium text-foreground text-sm leading-snug">{item.article}</div>
                    <div className="text-xs text-muted-foreground mt-1">{item.source}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-secondary/30 rounded-lg text-center">
                      <div className="text-xs text-muted-foreground">Current Mapping</div>
                      <div className="font-mono font-bold text-lg text-foreground">{item.mapped}</div>
                    </div>
                    <div className="p-3 bg-primary/10 rounded-lg text-center">
                      <div className="text-xs text-muted-foreground">Suggested Fix</div>
                      <div className="font-mono font-bold text-lg text-primary">{item.suggested}</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-mono font-semibold" style={{ color: item.confidence >= 0.7 ? "#10B981" : item.confidence >= 0.5 ? "#F59E0B" : "#EF4444" }}>{Math.round(item.confidence * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Reported by</span>
                    <Badge variant={item.reporter === "user" ? "hype" : "default"} className="text-xs">{item.reporter === "user" ? "User report" : "Auto-flagged"}</Badge>
                  </div>
                </div>
                <div className="mt-5 space-y-2">
                  <Btn variant="primary" className="w-full justify-center" icon={<Check size={13} />} onClick={() => { resolve(item.id, "approve"); }}>Approve & Remap to {item.suggested}</Btn>
                  <Btn variant="secondary" className="w-full justify-center" icon={<Archive size={13} />} onClick={() => resolve(item.id, "dismiss")}>Dismiss Report</Btn>
                  <Btn variant="secondary" className="w-full justify-center" icon={<RefreshCw size={13} />} onClick={() => resolve(item.id, "reroute")}>Re-route to Fuzzy Search</Btn>
                </div>
              </Card>
            );
          })() : (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              <div className="text-center">
                <AlertTriangle size={24} className="mx-auto mb-2 opacity-30" />
                <p>Select a record to review</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 22: Admin Users
// ────────────────────────────────────────────────

export default AdminMappingPage;
