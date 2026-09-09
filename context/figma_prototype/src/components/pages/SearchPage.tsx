// ────────────────────────────────────────────────
// SEARCH PAGE
// ────────────────────────────────────────────────

import { useState, useEffect, useCallback } from "react";
import { useTickerSearch, useTickerSearch as useSearch } from "../hooks";
import { Card, Badge, Button as Btn, ChevronRight, Filter, Search, TrendingUp, TrendingDown } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface TrackedTicker {
  ticker: string;
  name: string;
  sector?: string;
  current_price?: number;
  change_percent?: number;
  evidence_score?: number;
  hype_score?: number;
  price_as_of?: string;
}

export function SearchPage({ navigate, setSelectedTicker }: { navigate: (p: string) => void; setSelectedTicker: (t: string) => void }) {
  const [query, setQuery] = useState("NVDA");
  const [filterSector, setFilterSector] = useState("all");
  const [sortBy, setSortBy] = useState("ticker");
  const { results, loading, error, search } = useTickerSearch(query, { limit: 20, sector: filterSector, sortBy });

  const handleSearch = useCallback(() => {
    search();
  }, [search]);

  useEffect(() => {
    const timeout = setTimeout(() => search(), 300);
    return () => clearTimeout(timeout);
  }, [query, filterSector, sortBy, search]);

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
        <Button variant="secondary" icon={<Filter size={14} />}>Filter</Button>
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
            <option value="ticker">Ticker</option>
            <option value="evidence">Highest Evidence</option>
            <option value="hype">Highest Hype</option>
          </select>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {loading ? "Searching..." : error ? "Error loading results" : `${results.length} results for <strong className="text-foreground">"{query}"</strong>`}
      </div>

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
                <span className="font-mono font-bold text-xs text-foreground">{t.ticker.slice(0, 2)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-1">
                  <span className="font-mono font-bold text-sm text-foreground">{t.ticker}</span>
                  {t.sector && <span className="text-muted-foreground text-xs truncate">{t.sector}</span>}
                </div>
                <div className="mt-1.5 flex items-center gap-3">
                  {t.current_price !== undefined && (
                    <span className="font-mono text-sm font-semibold text-foreground">${t.current_price.toLocaleString()}</span>
                  )}
                  {t.change_percent !== undefined && (
                    <span className={cn("flex items-center gap-0.5", t.change_percent > 0 ? "text-emerald-400" : "text-red-400")}>
                      {t.change_percent > 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {t.change_percent > 0 ? "+" : ""}{t.change_percent}%
                    </span>
                  )}
                  {t.price_as_of && <span className="text-xs text-muted-foreground">as of {new Date(t.price_as_of).toLocaleDateString()}</span>}
                  {t.sector && <span className="text-xs text-muted-foreground px-2 py-0.5 bg-secondary rounded">{t.sector}</span>}
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

export default SearchPage;