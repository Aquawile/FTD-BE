import { useEffect, useMemo, useState } from "react";
import { FirebaseUser } from "firebase/auth";
import * as RechartsPrimitive from "recharts";
import { ChartContainer } from "../app/components/ui/chart";
import { apiRequest } from "../api";
import { Badge, Card, cn } from "./ui";

// Mirrors app.models.PriceTimeline (GET /tickers/{ticker}/price-timeline).
interface PriceTimelinePoint {
  date: string;
  close: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  percent_change: number | null;
  has_data: boolean;
}

interface PriceTimelineData {
  ticker: string;
  window_days: number;
  window_start: string | null;
  window_end: string | null;
  first_data_date: string | null;
  last_data_date: string | null;
  trading_days: number;
  days_covered: number;
  fill_ratio: number;
  points: PriceTimelinePoint[];
}

const fmtDate = (iso: string, opts: Intl.DateTimeFormatOptions) =>
  new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", ...opts });

function TimelineTooltip({ active, payload }: { active?: boolean; payload?: { payload: PriceTimelinePoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs shadow-lg">
      <div className="text-muted-foreground">{fmtDate(p.date, { month: "short", day: "numeric", year: "numeric" })}</div>
      {p.has_data && p.close != null ? (
        <div className="font-mono font-semibold text-foreground">
          ${p.close.toFixed(2)}
          {p.percent_change != null && (
            <span className={cn("ml-1.5", p.percent_change >= 0 ? "text-emerald-400" : "text-red-400")}>
              {p.percent_change >= 0 ? "+" : ""}{p.percent_change.toFixed(2)}%
            </span>
          )}
        </div>
      ) : (
        <div className="text-muted-foreground italic">No quote yet</div>
      )}
    </div>
  );
}

export function PriceTimeline({ ticker, firebaseUser }: { ticker: string; firebaseUser: FirebaseUser | null }) {
  const [data, setData] = useState<PriceTimelineData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!ticker || !firebaseUser) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(false);
    apiRequest(`/tickers/${ticker}/price-timeline`, firebaseUser)
      .then(r => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((d: PriceTimelineData) => { if (!cancelled) setData(d); })
      .catch(() => { if (!cancelled) setError(true); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [ticker, firebaseUser]);

  const { yDomain, monthTicks, lineColor } = useMemo(() => {
    const quoted = (data?.points ?? []).filter(p => p.has_data && p.close != null);
    if (quoted.length === 0) return { yDomain: [0, 1] as [number, number], monthTicks: [] as string[], lineColor: "#10B981" };
    const lows = quoted.map(p => p.low ?? p.close!);
    const highs = quoted.map(p => p.high ?? p.close!);
    const up = quoted[quoted.length - 1].close! >= quoted[0].close!;
    return {
      yDomain: [Math.min(...lows) * 0.98, Math.max(...highs) * 1.02] as [number, number],
      monthTicks: data!.points.filter((p, i) => i === 0 || p.date.endsWith("-01")).map(p => p.date),
      lineColor: up ? "#10B981" : "#EF4444",
    };
  }, [data]);

  const header = (
    <div className="flex items-center justify-between mb-3 gap-3">
      <h3 className="font-semibold text-sm">Price Timeline</h3>
      {data && data.trading_days > 0 && (
        <div className="flex items-center gap-2">
          <Badge variant="neutral" className="text-xs">{data.trading_days} trading days</Badge>
          <Badge variant="neutral" className="text-xs">{data.days_covered}/{data.window_days} days filled</Badge>
        </div>
      )}
    </div>
  );

  if (loading || error || !data || data.trading_days === 0) {
    const msg = loading ? "Loading price history…" : error ? "Unable to load price history." : `No price data available for ${ticker}.`;
    return (
      <Card className="p-5">
        {header}
        <div className={cn("h-[220px] flex items-center justify-center text-muted-foreground text-xs", loading && "animate-pulse")}>{msg}</div>
      </Card>
    );
  }

  return (
    <Card className="p-5">
      {header}
      <div className="h-[220px]">
        <ChartContainer config={{ close: { label: "Close", color: lineColor } }} className="h-full w-full aspect-auto">
          <RechartsPrimitive.ComposedChart data={data.points} margin={{ top: 5, right: 5, left: -15, bottom: 5 }}>
            <RechartsPrimitive.CartesianGrid strokeDasharray="2 2" vertical={false} stroke="#374151" opacity={0.3} />
            <RechartsPrimitive.YAxis
              domain={yDomain}
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            />
            <RechartsPrimitive.XAxis
              dataKey="date"
              ticks={monthTicks}
              interval={0}
              tick={{ fontSize: 10, fill: "#9CA3AF" }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: string) => fmtDate(v, { month: "short" })}
            />
            <RechartsPrimitive.Tooltip content={<TimelineTooltip />} cursor={{ stroke: "#6B7280", strokeDasharray: "3 3" }} />
            {data.last_data_date && (
              <RechartsPrimitive.ReferenceLine x={data.last_data_date} stroke="#6B7280" strokeDasharray="3 3" />
            )}
            <RechartsPrimitive.Area
              type="monotone"
              dataKey="close"
              connectNulls
              stroke={lineColor}
              strokeWidth={1.5}
              fill={lineColor}
              fillOpacity={0.1}
              dot={false}
              activeDot={{ r: 3, strokeWidth: 1, fill: "#F9FAFB" }}
              isAnimationActive={false}
            />
          </RechartsPrimitive.ComposedChart>
        </ChartContainer>
      </div>
      <div className="mt-3">
        <div className="h-1 rounded-full bg-secondary overflow-hidden">
          <div className="h-full rounded-full bg-primary/60" style={{ width: `${Math.min(100, data.fill_ratio * 100)}%` }} />
        </div>
        <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
          <span>{data.window_start && fmtDate(data.window_start, { month: "short", day: "numeric", year: "numeric" })}</span>
          <span>Latest quote {data.last_data_date && fmtDate(data.last_data_date, { month: "short", day: "numeric" })} · fills daily from Finnhub</span>
          <span>{data.window_end && fmtDate(data.window_end, { month: "short", day: "numeric", year: "numeric" })}</span>
        </div>
      </div>
    </Card>
  );
}

export default PriceTimeline;
