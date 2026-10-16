// ARCHIVED 2026-10-16: hype/evidence score UI. No API computes these scores yet
// (tickers.hype_score / evidence_score are default 50s), so they were removed from
// live pages. Restore by importing from here once a scoring endpoint exists.
export function getHypeColor(score: number): string {
  if (score >= 80) return "#F97316";
  if (score >= 60) return "#F59E0B";
  if (score >= 40) return "#EAB308";
  return "#10B981";
}

export function getEvidenceColor(score: number): string {
  if (score >= 80) return "#10B981";
  if (score >= 60) return "#34D399";
  if (score >= 40) return "#6EE7B7";
  return "#F97316";
}

export interface ScorePillProps {
  label: string;
  score: number;
  type: "hype" | "evidence";
}

export function ScorePill({ label, score, type }: ScorePillProps) {
  const color = type === "hype" ? getHypeColor(score) : getEvidenceColor(score);
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground font-medium">{label}</span>
        <span className="font-mono font-semibold" style={{ color }}>{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden w-32">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${score}%`, background: color }} />
      </div>
    </div>
  );
}

export interface HypeEvidenceBarProps {
  hype: number;
  evidence: number;
  showLabels?: boolean;
}

export function HypeEvidenceBar({ hype, evidence, showLabels = true }: HypeEvidenceBarProps) {
  return (
    <div className="space-y-2">
      {showLabels && (
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Hype Score</span>
          <span>Evidence Score</span>
        </div>
      )}
      <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-secondary">
        <div className="h-full transition-all" style={{ width: `${hype}%`, background: `linear-gradient(90deg, #F97316, #F59E0B)` }} />
      </div>
      <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-secondary">
        <div className="h-full transition-all" style={{ width: `${evidence}%`, background: `linear-gradient(90deg, #10B981, #34D399)` }} />
      </div>
      {showLabels && (
        <div className="flex items-center justify-between text-xs font-mono">
          <span style={{ color: getHypeColor(hype) }}>{hype}/100</span>
          <span style={{ color: getEvidenceColor(evidence) }}>{evidence}/100</span>
        </div>
      )}
    </div>
  );
}

