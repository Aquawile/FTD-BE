import { useState, useEffect, useCallback, useRef } from "react";
import type { User as FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Badge, Btn, Card, cn } from "../ui";
import { Activity, AlertTriangle, ArrowRight, Check, FileText, Plus } from "lucide-react";
import { toast } from "sonner";
import { useAlerts } from "../../hooks";
import { useTrackedTickers } from "../../hooks/tickerHooks";
import {
  createAlertSubscription,
  fetchUpdateWorkspace,
  fetchWorkspaces,
  getAlertSubscriptions,
  setAlertForTickers,
  markAlertsRead,
  updateAlertSubscription,
} from "../../api";
import type { AlertSubscription, AlertSubscriptionType, TrackedTicker, WorkspaceResponse } from "../../types";

const SUBSCRIPTION_TYPES: { value: AlertSubscriptionType; label: string }[] = [
  { value: "price_above", label: "Price closes above" },
  { value: "price_below", label: "Price closes below" },
  { value: "news", label: "New news articles" },
  { value: "filing", label: "New SEC filing" },
];
const isPriceType = (t: AlertSubscriptionType) => t === "price_above" || t === "price_below";

function describeSubscription(s: AlertSubscription) {
  const label = SUBSCRIPTION_TYPES.find(t => t.value === s.alert_type)?.label ?? s.alert_type;
  return isPriceType(s.alert_type) && s.threshold != null ? `${label} $${s.threshold.toLocaleString()}` : label;
}

// Only the subscriptions the user has actually created are listed and toggleable.
// They are checked at the end of each data sync, the only time ticker data changes.
function AlertSubscriptions({ firebaseUser, trackedTickers, prefillTicker, onPrefillUsed }: { firebaseUser: FirebaseUser | null; trackedTickers: TrackedTicker[]; prefillTicker?: string | null; onPrefillUsed?: () => void }) {
  const [subs, setSubs] = useState<AlertSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(!!prefillTicker);
  const [ticker, setTicker] = useState(prefillTicker || "");
  useEffect(() => { if (prefillTicker) onPrefillUsed?.(); }, []);  // one-shot hand-off from the ticker page
  const [alertType, setAlertType] = useState<AlertSubscriptionType>("price_above");
  const [threshold, setThreshold] = useState("");
  const [saving, setSaving] = useState(false);
  // An alert can target one ticker or a whole workspace (news / filing only: a price level
  // only makes sense for a single ticker).
  const [targetKind, setTargetKind] = useState<"ticker" | "workspace">("ticker");
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspaces, setWorkspaces] = useState<WorkspaceResponse[]>([]);
  useEffect(() => { fetchWorkspaces(firebaseUser).then(setWorkspaces).catch(() => undefined); }, [firebaseUser]);
  const workspaceMode = targetKind === "workspace";
  const chosenWorkspace = workspaces.find(w => String(w.id) === workspaceId);
  const typeOptions = workspaceMode ? SUBSCRIPTION_TYPES.filter(t => !isPriceType(t.value)) : SUBSCRIPTION_TYPES;
  const switchTarget = (kind: "ticker" | "workspace") => {
    setTargetKind(kind);
    if (kind === "workspace" && isPriceType(alertType)) setAlertType("news");
  };

  const load = useCallback(() => {
    setLoading(true);
    getAlertSubscriptions(firebaseUser)
      .then(data => { setSubs(data); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [firebaseUser]);

  useEffect(() => { load(); }, [load]);

  const toggle = async (s: AlertSubscription) => {
    setSubs(prev => prev.map(x => x.id === s.id ? { ...x, active: !s.active } : x));
    try {
      const updated = await updateAlertSubscription(firebaseUser, s.id, { active: !s.active });
      setSubs(prev => prev.map(x => x.id === s.id ? updated : x));
    } catch (e: any) {
      setSubs(prev => prev.map(x => x.id === s.id ? s : x));
      setError(e.message);
    }
  };

  const addForWorkspace = async () => {
    if (!chosenWorkspace) return;
    setSaving(true);
    try {
      if (alertType === "filing") {
        // Same switch as the workspace's settings page: also covers tickers added later.
        await fetchUpdateWorkspace(chosenWorkspace.id, { alert_on_filings: true }, firebaseUser);
      } else {
        await setAlertForTickers(firebaseUser, chosenWorkspace.tickers, "news", true);
      }
      load();
      setAdding(false); setWorkspaceId(""); setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const add = async () => {
    if (workspaceMode) return addForWorkspace();
    const value = Number(threshold);
    if (!ticker || (isPriceType(alertType) && !(value > 0))) return;
    setSaving(true);
    try {
      const created = await createAlertSubscription(firebaseUser, {
        ticker, alert_type: alertType, threshold: isPriceType(alertType) ? value : null,
      });
      setSubs(prev => [...prev, created]);
      setAdding(false); setTicker(""); setThreshold(""); setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const inputCls = "bg-secondary border border-border rounded-lg px-2 py-1.5 text-xs text-foreground";

  return (
    <Card className="mt-6 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Alert Subscriptions</h3>
        {!adding && <Btn variant="secondary" size="sm" icon={<Plus size={12} />} onClick={() => setAdding(true)}>Add</Btn>}
      </div>
      {adding && (
        <div className="flex flex-wrap items-center gap-2 mb-4 pb-4 border-b border-border/50">
          <select className={inputCls} aria-label="Alert target" value={targetKind} onChange={e => switchTarget(e.target.value as "ticker" | "workspace")}>
            <option value="ticker">A ticker</option>
            <option value="workspace">A workspace</option>
          </select>
          {workspaceMode ? (
            <select className={inputCls} aria-label="Workspace" value={workspaceId} onChange={e => setWorkspaceId(e.target.value)}>
              <option value="">Workspace…</option>
              {workspaces.map(w => <option key={w.id} value={String(w.id)}>{w.name} ({w.tickers.length} tickers)</option>)}
            </select>
          ) : (
            <select className={inputCls} aria-label="Ticker" value={ticker} onChange={e => setTicker(e.target.value)}>
              <option value="">Ticker…</option>
              {trackedTickers.slice().sort((a, b) => a.symbol.localeCompare(b.symbol)).map(t => <option key={t.symbol} value={t.symbol}>{t.symbol} — {t.name}</option>)}
            </select>
          )}
          <select className={inputCls} aria-label="Alert type" value={alertType} onChange={e => setAlertType(e.target.value as AlertSubscriptionType)}>
            {typeOptions.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          {!workspaceMode && isPriceType(alertType) && (
            <input className={cn(inputCls, "w-24")} type="number" min="0" step="0.01" placeholder="$ price" aria-label="Price threshold in dollars"
              value={threshold} onChange={e => setThreshold(e.target.value)} />
          )}
          <Btn size="sm" onClick={add} disabled={saving || (workspaceMode ? !chosenWorkspace || chosenWorkspace.tickers.length === 0 : !ticker || (isPriceType(alertType) && !(Number(threshold) > 0)))}>
            {saving ? "Saving…" : "Save"}
          </Btn>
          <Btn variant="ghost" size="sm" onClick={() => { setAdding(false); setError(null); }}>Cancel</Btn>
        </div>
      )}
      {error && <p className="text-xs text-red-400 mb-3">{error}</p>}
      <div className="space-y-3 text-sm">
        {subs.map(s => (
          <div key={s.id} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0 gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-mono font-semibold text-xs text-foreground w-12">{s.ticker}</span>
                <span className="text-xs text-foreground">{describeSubscription(s)}</span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5 ml-14">
                {s.last_evaluated_at ? `Last checked: ${s.last_observed_label}` : "Checked after the next data sync"}
              </p>
            </div>
            <button
              type="button" role="switch" aria-checked={s.active} aria-label={`${s.active ? "Pause" : "Resume"} ${s.ticker} alert`}
              onClick={() => toggle(s)}
              className={cn("relative inline-flex w-8 h-5 rounded-full cursor-pointer transition-colors shrink-0", s.active ? "bg-primary" : "bg-secondary border border-border")}
            >
              <span className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform", s.active ? "translate-x-3.5" : "translate-x-0.5")} />
            </button>
          </div>
        ))}
        {!loading && subs.length === 0 && !error && (
          <p className="text-xs text-muted-foreground text-center py-4">No subscriptions yet. Add one to get alerted when a ticker changes.</p>
        )}
        {loading && <p className="text-xs text-muted-foreground text-center py-4">Loading subscriptions…</p>}
      </div>
    </Card>
  );
}

function AlertsPage({ navigate, setSelectedTicker, firebaseUser, onAlertsChanged, prefillTicker, onPrefillUsed }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; firebaseUser: FirebaseUser | null; onAlertsChanged?: () => void; prefillTicker?: string | null; onPrefillUsed?: () => void }) {
  const { alerts: ALERTS_DATA, loading, error, refetch } = useAlerts(50, firebaseUser);
  const { tickers: trackedTickers } = useTrackedTickers(500);
  const [filter, setFilter] = useState("all");
  // Alerts that were unread when this page opened stay highlighted for this visit, but are
  // marked read on the server straight away: looking at an alert clears the bell and nav badge.
  const [freshIds, setFreshIds] = useState<Set<number>>(new Set());
  const markedRef = useRef<Set<number>>(new Set());
  const isUnread = (a: { id: number | string; read?: boolean }) => !a.read || freshIds.has(Number(a.id));
  const unreadCount = ALERTS_DATA.filter(isUnread).length;

  useEffect(() => {
    if (loading) return;
    const ids = ALERTS_DATA.filter(a => !a.read && !markedRef.current.has(Number(a.id))).map(a => Number(a.id));
    if (ids.length === 0) return;
    ids.forEach(id => markedRef.current.add(id));
    setFreshIds(prev => new Set([...prev, ...ids]));
    markAlertsRead(firebaseUser, ids).then(() => onAlertsChanged?.()).catch(() => ids.forEach(id => markedRef.current.delete(id)));
  }, [loading, ALERTS_DATA]);  // eslint-disable-line react-hooks/exhaustive-deps

  const markAllRead = async () => {
    await markAlertsRead(firebaseUser).catch(() => undefined);
    toast.dismiss();
    setFreshIds(new Set());
    refetch();
    onAlertsChanged?.();
  };

  const filtered = filter === "all"
    ? ALERTS_DATA
    : filter === "unread"
      ? ALERTS_DATA.filter(isUnread)
      : ALERTS_DATA.filter(a => a.severity === filter);

  const alertTypeIcon = (type: string) =>
    type === "filing" ? <FileText size={14} /> : type === "narrative_shift" ? <Activity size={14} /> : <AlertTriangle size={14} />;

  const alertTypeColor = (t: string) =>
    t === "filing" ? "#10B981" : t === "narrative_shift" ? "#F59E0B" : "#F97316";

  if (loading) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Alerts</h1>
            <p className="text-muted-foreground text-sm mt-0.5">Loading alerts...</p>
          </div>
        </div>
        <div className="animate-pulse space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="h-3 bg-secondary rounded w-3/4" /></Card>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <Card className="p-4 text-sm text-red-400">Unable to load alerts</Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{unreadCount} unread notifications</p>
        </div>
        <Btn variant="secondary" size="sm" icon={<Check size={12} />} onClick={markAllRead} disabled={unreadCount === 0}>Mark all read</Btn>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {["all", "unread", "high", "medium", "low"].map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-lg text-xs border capitalize cursor-pointer transition-all", filter === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}>{f}</button>
        ))}
      </div>
      <div className="space-y-3">
        {filtered.map(a => (
          <Card key={a.id} className={cn("p-4 transition-all cursor-pointer hover:border-primary/30", isUnread(a) && "border-primary/20 bg-primary/3")}>
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${alertTypeColor(a.type)}15` }}>
                <span style={{ color: alertTypeColor(a.type) }}>{alertTypeIcon(a.type)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono font-bold text-sm text-foreground">{a.ticker || "—"}</span>
                  <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "warning" : "neutral"} className="text-xs">{a.severity}</Badge>
                  <Badge variant="neutral" className="text-xs capitalize">{a.type?.replace("_", " ") || "—"}</Badge>
                  {isUnread(a) && <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block" />}
                </div>
                <p className="text-sm text-foreground">{a.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{a.time}</p>
              </div>
              {a.ticker && (
                <Btn variant="ghost" size="sm" onClick={() => { setSelectedTicker(a.ticker); navigate("ticker"); }} icon={<ArrowRight size={12} />}>View</Btn>
              )}
            </div>
          </Card>
        ))}
        {filtered.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">No alerts match your filter.</p>
        )}
      </div>

      <AlertSubscriptions firebaseUser={firebaseUser} trackedTickers={trackedTickers} prefillTicker={prefillTicker} onPrefillUsed={onPrefillUsed} />
    </div>
  );
}

export default AlertsPage;