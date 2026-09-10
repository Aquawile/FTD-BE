import { useState, useEffect } from "react";
import { Page } from "../../app/types";
import { Btn, Card, cn } from "../ui";
import { AlertCircle, ChevronRight, Filter, Search } from "lucide-react";

function SearchPage({ navigate, setSelectedTicker }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void }) {
  const [query, setQuery] = useState("NVDA");
  const [filterSector, setFilterSector] = useState("all");
  const [sortBy, setSortBy] = useState("divergence");
  const [results, setResults] = useState<Array<{ ticker: string; cik: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(false);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    fetch(`http://localhost:8000/tickers/search?q=${encodeURIComponent(query)}&limit=20`, { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => setResults(Array.isArray(data) ? data : []))
      .catch(err => {
        if (err.name === "AbortError") {
          setError(true);
        } else {
          setError(true);
        }
      })
      .finally(() => {
        clearTimeout(timeout);
        setLoading(false);
      });
  }, [query]);

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-xl">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search tickers, companies, or topics..."
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
            <option value="divergence">Hype/Evidence Gap</option>
            <option value="hype">Highest Hype</option>
            <option value="evidence">Highest Evidence</option>
          </select>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">{loading ? "Searching..." : error ? "Error loading results" : `${results.length} results for <strong className=\"text-foreground\">\"${query}\"</strong>`}</div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="text-center py-12 text-muted-foreground">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to reach the research database.</p>
        </div>
      )}

      {!loading && !error && results.length === 0 && query.trim() && (
        <div className="text-center py-12 text-muted-foreground">
          <p>No tickers found matching "{query}"</p>
        </div>
      )}

      <div className="space-y-3">
        {results.map(t => (
          <Card key={t.ticker} className="p-5 cursor-pointer hover:border-primary/30 transition-all" onClick={() => { setSelectedTicker(t.ticker); navigate("ticker"); }}>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-secondary flex items-center justify-center shrink-0">
                <span className="font-mono font-bold text-sm text-foreground">{t.ticker.slice(0, 2)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono font-bold text-base text-foreground">{t.ticker}</span>
                  <span className="text-muted-foreground text-sm">{t.cik}</span>
                </div>
              </div>
              <ChevronRight size={16} className="text-muted-foreground shrink-0" />
            </div>
          </Card>
        ))}
      </div>

      {/* Related searches */}
      <div>
        <div className="text-xs text-muted-foreground mb-2">Related searches</div>
        <div className="flex gap-2 flex-wrap">
          {["AI chip shortage", "data center capex 2024", "GPU supply chain", "semiconductor earnings"].map(r => (
            <button key={r} className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 cursor-pointer transition-all">{r}</button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 9: Ticker Research Dashboard
// ────────────────────────────────────────────────

export default SearchPage;
