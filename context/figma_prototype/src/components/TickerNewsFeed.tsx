import { useEffect, useState } from "react";
import { FirebaseUser } from "firebase/auth";
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, ExternalLink } from "lucide-react";
import { apiRequest } from "../api";
import { Badge, Btn, Card, cn } from "./ui";

// One page of GET /tickers/{ticker}/news; the API also returns
// X-Total-Count (articles in range) and X-Earliest-Date (ticker's oldest article).
interface NewsRow {
  target_ticker: string;
  normalized_calendar_date: string | null;
  ingest_date: string | null;
  content_body: string;
  source: string | null;
  url: string | null;
}

const PAGE_SIZE = 20;
const ALL_START = "2000-01-01";
type Preset = "30d" | "90d" | "1y" | "all" | "custom";

const isoDaysAgo = (days: number) => new Date(Date.now() - days * 86_400_000).toISOString().slice(0, 10);
const today = () => new Date().toISOString().slice(0, 10);

function rangeFor(preset: Preset, from: string, to: string): { start: string; end: string } {
  switch (preset) {
    case "30d": return { start: isoDaysAgo(30), end: today() };
    case "90d": return { start: isoDaysAgo(90), end: today() };
    case "1y": return { start: isoDaysAgo(365), end: today() };
    case "all": return { start: ALL_START, end: today() };
    default: return { start: from || ALL_START, end: to || today() };
  }
}

function sourceLabel(source: string | null) {
  return source === "gnews" ? "Google News" : source === "finnhub" ? "Finnhub" : source === "sec" ? "SEC" : source || "News";
}

export function TickerNewsFeed({ ticker, firebaseUser }: { ticker: string; firebaseUser: FirebaseUser | null }) {
  const [preset, setPreset] = useState<Preset>("90d");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<NewsRow[]>([]);
  const [total, setTotal] = useState(0);
  const [earliest, setEarliest] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const { start, end } = rangeFor(preset, from, to);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  // A new ticker or range starts again at page 1.
  useEffect(() => { setPage(1); }, [ticker, preset, from, to]);

  useEffect(() => {
    if (!ticker || !firebaseUser) { setLoading(false); return; }
    let cancelled = false;
    setLoading(true);
    setError(false);
    const offset = (page - 1) * PAGE_SIZE;
    apiRequest(`/tickers/${ticker}/news?start=${start}&end=${end}&limit=${PAGE_SIZE}&offset=${offset}`, firebaseUser)
      .then(async r => {
        if (!r.ok) throw new Error(String(r.status));
        const data: NewsRow[] = await r.json();
        if (cancelled) return;
        setRows(data);
        setTotal(Number(r.headers.get("X-Total-Count") ?? data.length));
        setEarliest(r.headers.get("X-Earliest-Date"));
      })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, firebaseUser, start, end, page]);

  const presets: { id: Preset; label: string }[] = [
    { id: "30d", label: "30 days" },
    { id: "90d", label: "90 days" },
    { id: "1y", label: "1 year" },
    { id: "all", label: earliest ? `All (since ${earliest})` : "All" },
    { id: "custom", label: "Custom" },
  ];
  const firstShown = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastShown = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-semibold">News for {ticker}</h3>
        <div className="flex flex-wrap items-center gap-1.5">
          {presets.map(p => (
            <button
              key={p.id}
              onClick={() => {
                if (p.id === "custom" && !from) { setFrom(start); setTo(end); }
                setPreset(p.id);
              }}
              className={cn("px-2.5 py-1 rounded-lg text-xs border transition-all cursor-pointer",
                preset === p.id ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {preset === "custom" && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          <label className="flex items-center gap-1.5">From
            <input type="date" value={from} min={earliest ?? undefined} max={to || today()} onChange={e => setFrom(e.target.value)}
              className="bg-secondary border border-border rounded-lg px-2 py-1 text-foreground" />
          </label>
          <label className="flex items-center gap-1.5">To
            <input type="date" value={to} min={from || earliest || undefined} max={today()} onChange={e => setTo(e.target.value)}
              className="bg-secondary border border-border rounded-lg px-2 py-1 text-foreground" />
          </label>
        </div>
      )}

      <div className="text-xs text-muted-foreground">
        {loading ? "Loading articles…" : error ? "Unable to load articles." :
          total === 0 ? `No articles for ${ticker} between ${start} and ${end}.` :
          `Showing ${firstShown}–${lastShown} of ${total.toLocaleString()} articles (${start} to ${end}), newest first`}
      </div>

      {!loading && !error && rows.map((a, i) => {
        const headline = (a.content_body.split(". ")[0] + ".") || "Untitled";
        const summary = a.content_body.substring(headline.length).trim() || a.content_body;
        return (
          <Card key={`${page}-${i}`} className="p-5">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="neutral" className="text-xs">{sourceLabel(a.source)}</Badge>
              <span className="text-xs text-muted-foreground">{a.normalized_calendar_date?.slice(0, 10) || a.ingest_date?.slice(0, 10) || "Unknown date"}</span>
            </div>
            <h4 className="font-semibold text-sm text-foreground mb-2 leading-snug">{headline}</h4>
            <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">{summary}</p>
            {a.url && (
              <a href={a.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 mt-2">
                <ExternalLink size={12} /> View article
              </a>
            )}
          </Card>
        );
      })}

      {total > PAGE_SIZE && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Btn variant="secondary" size="sm" icon={<ChevronsLeft size={12} />} onClick={() => setPage(1)} disabled={page === 1 || loading}>Newest</Btn>
          <Btn variant="secondary" size="sm" icon={<ChevronLeft size={12} />} onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1 || loading}>Prev</Btn>
          <span className="text-xs text-muted-foreground px-2">Page {page} of {pages}</span>
          <Btn variant="secondary" size="sm" icon={<ChevronRight size={12} />} onClick={() => setPage(p => Math.min(pages, p + 1))} disabled={page >= pages || loading}>Next</Btn>
          <Btn variant="secondary" size="sm" icon={<ChevronsRight size={12} />} onClick={() => setPage(pages)} disabled={page >= pages || loading}>Oldest</Btn>
        </div>
      )}
    </div>
  );
}

export default TickerNewsFeed;
