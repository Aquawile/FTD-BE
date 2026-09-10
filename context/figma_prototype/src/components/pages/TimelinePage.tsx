import { useState } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Modal, cn, getHypeColor } from "../ui";
import { Activity, ArrowRight, Bell, BookOpen, ChevronLeft, Download, FileText, Globe, RefreshCw, Users } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function TimelinePage({ navigate, ticker }: { navigate: (p: Page) => void; ticker: string }) {
  const [showExport, setShowExport] = useState(false);
  const typeColors: Record<string, string> = {
    filing: "#10B981", narrative: "#F59E0B", news: "#3B82F6", social: "#F97316", earnings: "#8B5CF6",
  };
  const typeIcons: Record<string, React.ReactNode> = {
    filing: <FileText size={12} />, narrative: <Activity size={12} />, news: <Globe size={12} />, social: <Users size={12} />, earnings: <BarChart2 size={12} />,
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> {ticker}
        </button>
        <h1 className="text-xl font-bold flex-1">Narrative Timeline — {ticker}</h1>
        <div className="flex gap-2">
          <Btn variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>Subscribe to Alerts</Btn>
          <Btn variant="secondary" size="sm" icon={<Download size={12} />} onClick={() => setShowExport(true)}>Export View</Btn>
        </div>
      </div>

      {/* Score trend */}
      <Card className="p-4 mb-6">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium">Score Evolution</span>
          <Badge variant="neutral">Last 60 days</Badge>
        </div>
        <div className="h-16 flex items-end gap-1">
          {[54, 58, 61, 67, 71, 75, 68, 73, 79, 84, 81, 84].map((v, i) => (
            <div key={i} className="flex-1 rounded-t transition-all" style={{ height: `${(v / 100) * 64}px`, background: `linear-gradient(180deg, ${getHypeColor(v)}, ${getHypeColor(v)}80)` }} />
          ))}
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
          <span>May 1</span><span>May 15</span><span>Jun 1</span><span>Jun 18</span>
        </div>
      </Card>

      {/* Legend */}
      <div className="flex items-center gap-4 mb-4 flex-wrap">
        {Object.entries(typeColors).map(([t, c]) => (
          <div key={t} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className="w-2 h-2 rounded-full" style={{ background: c }} />
            <span className="capitalize">{t}</span>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
        <div className="space-y-4">
          {TIMELINE_EVENTS.map((ev, i) => (
            <div key={i} className="relative flex gap-5 pl-8">
              <div className="absolute left-0 top-3 w-8 h-8 rounded-full flex items-center justify-center border-2 border-background" style={{ background: typeColors[ev.type] }}>
                <span style={{ color: "#fff" }}>{typeIcons[ev.type]}</span>
              </div>
              <Card className="flex-1 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="text-xs capitalize" style={{ background: `${typeColors[ev.type]}15`, color: typeColors[ev.type], borderColor: `${typeColors[ev.type]}30` }}>{ev.type}</Badge>
                      <span className="text-xs text-muted-foreground">{ev.date}</span>
                    </div>
                    <h4 className="font-medium text-sm text-foreground mb-1">{ev.title}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">{ev.description}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className={cn("text-xs font-mono font-semibold", ev.score_delta > 0 ? "text-emerald-400" : ev.score_delta < 0 ? "text-red-400" : "text-muted-foreground")}>
                      {ev.score_delta > 0 ? "+" : ""}{ev.score_delta !== 0 ? ev.score_delta : "—"}
                    </div>
                    <div className="text-xs text-muted-foreground">delta</div>
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
        <div className="mt-6 text-center">
          <Btn variant="secondary" icon={<RefreshCw size={12} />}>Load Earlier Events</Btn>
        </div>
      </div>

      {showExport && (
        <Modal title="Export Timeline View" onClose={() => setShowExport(false)} size="sm">
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">Select your preferred export format. Source citation URLs will be included.</p>
            <div className="space-y-2">
              {[{ format: "CSV", desc: "Spreadsheet with all event data and scores", icon: <FileText size={16} /> }, { format: "PDF", desc: "Formatted report with timeline layout and citations", icon: <BookOpen size={16} /> }].map(f => (
                <button key={f.format} className="w-full flex items-center gap-3 p-3 bg-secondary/50 rounded-xl border border-border hover:border-primary/30 cursor-pointer transition-all text-left" onClick={() => setShowExport(false)}>
                  <div className="text-primary">{f.icon}</div>
                  <div>
                    <div className="font-medium text-sm">{f.format}</div>
                    <div className="text-xs text-muted-foreground">{f.desc}</div>
                  </div>
                  <ArrowRight size={14} className="ml-auto text-muted-foreground" />
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
// PAGE 11: SEC Filings
// ────────────────────────────────────────────────

export default TimelinePage;
