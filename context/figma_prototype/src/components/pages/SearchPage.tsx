import { useState, useEffect } from "react";
import { FirebaseUser } from "firebase/auth";
import { Page } from "../../app/types";
import { Btn, Card, cn } from "../ui";
import { AlertCircle, ChevronRight, Filter, Search, TrendingDown, TrendingUp } from "lucide-react";
import { apiRequest, API_BASE , formatPrice as formatSharedPrice } from "../../api";

interface TrackedTicker {
  symbol: string;
  name: string;
  sector: string | null;
  current_price: number | null;
  evidence_score: number | null;
  hype_score: number | null;
  change_percent: number | null;
  price_as_of: string | null;
}

function SearchPage({ navigate, setSelectedTicker, firebaseUser }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; firebaseUser: FirebaseUser | null }) {
  const [query, setQuery] = useState("");
  const [filterSector, setFilterSector] = useState("all");
  const [sortBy, setSortBy] = useState("symbol");
  const [tickers, setTickers] = useState<TrackedTicker[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchTickers = async () => {
      if (!firebaseUser) {
        setTickers([]);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(false);
      try {
        const res = await apiRequest("/tickers/tracked", firebaseUser);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setTickers(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      }
    };
    fetchTickers();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const filtered = tickers.filter(t => {
    if (query && !t.symbol.toLowerCase().includes(query.toLowerCase()) && !t.name.toLowerCase().includes(query.toLowerCase())) return false;
    if (filterSector !== "all" && t.sector?.toLowerCase() !== filterSector) return false;
    return true;
  });

  const sorted = filtered.slice().sort((a, b) => {
    if (sortBy === "change") return Math.abs(b.change_percent ?? 0) - Math.abs(a.change_percent ?? 0);
    return a.symbol.localeCompare(b.symbol);
  });

  const formatPrice = (price: number | null) => (price == null ? "—" : `$${formatSharedPrice(price)}`);

  const formatChange = (change: number | null) => {
    if (change === null) return "—";
    const arrow = change > 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />;
    return (
      <span className={`flex items-center gap-0.5 ${change > 0 ? "text-emerald-400" : "text-red-400"}`}>
        {arrow}
        {change > 0 ? "+" : ""}{change.toFixed(2)}%
      </span>
    );
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Search header */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-xl">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search tickers, companies..."
            className="w-full pl-9 pr-3 py-2.5 bg-input-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
          />
        </div>
        <Btn variant="secondary" icon={<Filter size={14} />}>Filter</Btn>
      </div>

      {/* Filter chips */}
      <div className="flex items-center gap-2 flex-wrap">
        {["all", "semiconductors", "ai", "ev", "cloud"].map(f => (
          <button
            key={f}
            onClick={() => setFilterSector(f)}
            className={cn("px-3 py-1 rounded-lg text-xs border transition-all cursor-pointer capitalize", filterSector === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}
          >
            {f === "all" ? "All sectors" : f.toUpperCase()}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Sort by:</span>
          <select value={sortBy} onChange={e => setSortBy(e.target.value)} className="bg-secondary border border-border rounded-lg text-xs px-2 py-1 text-foreground focus:outline-none">
            <option value="symbol">Symbol (A–Z)</option>
            <option value="change">Biggest daily move</option>
          </select>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {loading ? "Loading tickers..." : error ? "Error loading tickers" : `${sorted.length} tickers tracked`}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="text-center py-12 text-muted-foreground">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to load tickers.</p>
        </div>
      )}

      {!loading && !error && sorted.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p>No tickers found.</p>
        </div>
      )}

      {/* Ticker list */}
      <div className="space-y-3">
        {sorted.map(t => (
          <Card
            key={t.symbol}
            className="p-5 cursor-pointer hover:border-primary/30 transition-all"
            onClick={() => { setSelectedTicker(t.symbol); navigate("ticker"); }}
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center shrink-0">
                <span className="font-mono font-bold text-sm text-foreground">{t.symbol.slice(0, 2)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono font-bold text-base text-foreground">{t.symbol}</span>
                  <span className="text-muted-foreground text-sm">{t.name}</span>
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="font-mono font-bold text-lg text-foreground">{formatPrice(t.current_price)}</div>
                {formatChange(t.change_percent)}
              </div>
              <ChevronRight size={16} className="text-muted-foreground shrink-0" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

export default SearchPage;
