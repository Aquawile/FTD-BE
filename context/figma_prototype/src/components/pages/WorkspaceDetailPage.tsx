import { useState, useEffect } from "react";
import type { User as FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Input, Modal, cn } from "../ui";
import { ChevronLeft, Minus, Plus, Search, Settings, TrendingDown, TrendingUp } from "lucide-react";
import { apiRequest, fetchAddTickerToWorkspace, fetchRemoveTickerFromWorkspace } from "../../api";
import { TrackedTicker, WorkspaceResponse } from "../../types";

function WorkspaceDetailPage({ navigate, setSelectedTicker, selectedWorkspace, firebaseUser, refreshWorkspace }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; selectedWorkspace: WorkspaceResponse | null; firebaseUser: FirebaseUser | null; refreshWorkspace: () => void }) {
  const ws = selectedWorkspace || { id: 0, name: "", tickers: [], alerts: 0, created_at: null };
  const [showAdd, setShowAdd] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [trackedTickers, setTrackedTickers] = useState<TrackedTicker[]>([]);
  const [tickersLoading, setTickersLoading] = useState(false);

  useEffect(() => {
    if (!firebaseUser) {
      setTrackedTickers([]);
      return;
    }
    let cancelled = false;
    const loadTickers = async () => {
      setTickersLoading(true);
      try {
        const res = await apiRequest("/tickers/tracked?limit=500", firebaseUser);
        if (!res.ok) throw new Error("Failed to fetch tracked tickers");
        const data: TrackedTicker[] = await res.json();
        if (!cancelled) setTrackedTickers(data);
      } catch {
        if (!cancelled) setTrackedTickers([]);
      } finally {
        if (!cancelled) setTickersLoading(false);
      }
    };
    loadTickers();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const filteredTickers = trackedTickers.filter(t =>
    t.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (t.name || "").toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleAddTicker = async (symbol: string) => {
    if (!firebaseUser || !ws.id) return;
    try {
      await fetchAddTickerToWorkspace(ws.id, symbol, firebaseUser);
      if (refreshWorkspace) refreshWorkspace();
      else setShowAdd(false);
    } catch {
      // error handling
    }
    setShowAdd(false);
  };

  const handleRemoveTicker = async (symbol: string) => {
    if (!firebaseUser || !ws.id) return;
    try {
      await fetchRemoveTickerFromWorkspace(ws.id, symbol, firebaseUser);
      if (refreshWorkspace) refreshWorkspace();
    } catch {
      // error handling
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspaces")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Workspaces</button>
        <h1 className="text-xl font-bold flex-1">{ws.name || "Untitled Workspace"}</h1>
        <Badge variant="neutral">{ws.tickers.length} / 50 tickers</Badge>
        <Btn variant="secondary" size="sm" icon={<Settings size={12} />} onClick={() => navigate("workspace-settings")}>Settings</Btn>
        <Btn variant="primary" size="sm" icon={<Plus size={12} />} onClick={() => setShowAdd(true)}>Add Ticker</Btn>
      </div>

      {/* Workspace stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Tickers Tracked", value: ws.tickers.length.toString() || "0", color: "#8B5CF6" },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="font-mono font-bold text-2xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {ws.tickers.map(symbol => {
          const t = trackedTickers.find(tt => tt.symbol === symbol);
          const displayTicker: TrackedTicker = t || { symbol, name: symbol, sector: "" };
          return (
            <Card key={symbol} className="p-4 cursor-pointer hover:border-primary/30 transition-all" onClick={() => { setSelectedTicker(symbol); navigate("ticker"); }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className="w-9 h-9 rounded-xl bg-secondary flex items-center justify-center">
                    <span className="font-mono font-bold text-xs text-foreground">{symbol.slice(0, 2)}</span>
                  </div>
                  <div>
                    <div className="font-mono font-semibold text-sm text-foreground">{symbol}</div>
                    {displayTicker.name && displayTicker.name !== symbol && (
                      <div className="text-xs text-muted-foreground truncate max-w-[10rem]">{displayTicker.name}</div>
                    )}
                    {displayTicker.current_price && (
                      <div className="text-xs text-muted-foreground mt-0.5">${displayTicker.current_price.toFixed(2)}</div>
                    )}
                  </div>
                </div>
                <button
                  className="p-1 text-muted-foreground hover:text-red-400 cursor-pointer"
                  onClick={e => { e.stopPropagation(); handleRemoveTicker(symbol); }}
                >
                  <Minus size={14} />
                </button>
              </div>
              {t && (
                <div className="text-xs text-muted-foreground">
                  {t.change_percent !== undefined && t.change_percent !== null ? (
                    <span className={cn("flex items-center gap-0.5", t.change_percent > 0 ? "text-emerald-400" : t.change_percent < 0 ? "text-red-400" : "")}>
                      {t.change_percent > 0 ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                      {t.change_percent > 0 ? "+" : ""}{t.change_percent}%
                    </span>
                  ) : "No price data"}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {showAdd && (
        <Modal title="Add Ticker to Workspace" onClose={() => setShowAdd(false)} size="sm">
          <div className="space-y-4">
            <Input
              placeholder="Search ticker or company name..."
              icon={<Search size={14} />}
              value={searchQuery}
              onChange={setSearchQuery}
            />
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {tickersLoading ? (
                <div className="text-center py-4 text-xs text-muted-foreground">Loading tickers...</div>
              ) : filteredTickers.length === 0 ? (
                <div className="text-center py-4 text-xs text-muted-foreground">No tickers found</div>
              ) : (
                filteredTickers.map(t => (
                  <button
                    key={t.symbol}
                    className="w-full flex items-center gap-3 p-2.5 rounded-lg hover:bg-secondary cursor-pointer text-left transition-all"
                    onClick={() => handleAddTicker(t.symbol)}
                  >
                    <span className="font-mono font-semibold text-sm w-12 text-foreground">{t.symbol}</span>
                    <span className="text-xs text-muted-foreground flex-1">{t.name || ""}</span>
                    <Plus size={12} className="text-muted-foreground" />
                  </button>
                ))
              )}
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default WorkspaceDetailPage;
