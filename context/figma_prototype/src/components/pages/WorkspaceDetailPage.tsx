import { useState } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, HypeEvidenceBar, Input, Modal, cn } from "../ui";
import { ChevronLeft, Minus, Plus, Search, Settings, TrendingDown, TrendingUp } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function WorkspaceDetailPage({ navigate, setSelectedTicker }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void }) {
  const ws = WORKSPACES[0];
  const [showAdd, setShowAdd] = useState(false);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspaces")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Workspaces</button>
        <h1 className="text-xl font-bold flex-1">{ws.name}</h1>
        <Badge variant="neutral">{ws.tickers.length} / 50 tickers</Badge>
        <Btn variant="secondary" size="sm" icon={<Settings size={12} />} onClick={() => navigate("workspace-settings")}>Settings</Btn>
        <Btn variant="primary" size="sm" icon={<Plus size={12} />} onClick={() => setShowAdd(true)}>Add Ticker</Btn>
      </div>

      {/* Workspace avg scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Avg Hype Score", value: "82", color: "#F59E0B" },
          { label: "Avg Evidence Score", value: "66", color: "#10B981" },
          { label: "Active Alerts", value: "3", color: "#3B82F6" },
          { label: "Tickers Tracked", value: ws.tickers.length.toString(), color: "#8B5CF6" },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="font-mono font-bold text-2xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {TICKERS.filter(t => ws.tickers.includes(t.symbol)).map(t => (
          <Card key={t.symbol} className="p-4 cursor-pointer hover:border-primary/30 transition-all" onClick={() => { setSelectedTicker(t.symbol); navigate("ticker"); }}>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-9 h-9 rounded-xl bg-secondary flex items-center justify-center">
                  <span className="font-mono font-bold text-xs">{t.symbol.slice(0, 2)}</span>
                </div>
                <div>
                  <div className="font-mono font-semibold text-sm text-foreground">{t.symbol}</div>
                  <div className={cn("text-xs flex items-center gap-0.5", t.change > 0 ? "text-emerald-400" : "text-red-400")}>
                    {t.change > 0 ? <TrendingUp size={9} /> : <TrendingDown size={9} />}{t.change > 0 ? "+" : ""}{t.change}%
                  </div>
                </div>
              </div>
              <button className="p-1 text-muted-foreground hover:text-red-400 cursor-pointer" onClick={e => e.stopPropagation()}>
                <Minus size={14} />
              </button>
            </div>
            <HypeEvidenceBar hype={t.hype} evidence={t.evidence} />
          </Card>
        ))}
      </div>

      {showAdd && (
        <Modal title="Add Ticker to Workspace" onClose={() => setShowAdd(false)} size="sm">
          <div className="space-y-4">
            <Input placeholder="Search ticker or company name..." icon={<Search size={14} />} />
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {TICKERS.map(t => (
                <button key={t.symbol} className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-secondary cursor-pointer text-left transition-all" onClick={() => setShowAdd(false)}>
                  <span className="font-mono font-semibold text-sm w-12 text-foreground">{t.symbol}</span>
                  <span className="text-xs text-muted-foreground flex-1">{t.name}</span>
                  <Plus size={12} className="text-muted-foreground" />
                </button>
              ))}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 16: Workspace Settings
// ────────────────────────────────────────────────

export default WorkspaceDetailPage;
