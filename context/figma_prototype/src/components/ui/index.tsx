import { X, FileText, Bell, Target, TrendingUp, TrendingDown } from "lucide-react";

export { X, FileText, Bell, Target, TrendingUp, TrendingDown };

export function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(" ");
}

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

export type BadgeVariant = "default" | "evidence" | "hype" | "neutral" | "danger" | "purple" | "outline";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  const styles: Record<BadgeVariant, string> = {
    default: "bg-primary/15 text-primary border-primary/20",
    evidence: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    hype: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    neutral: "bg-secondary text-muted-foreground border-border",
    danger: "bg-red-500/10 text-red-400 border-red-500/20",
    purple: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    outline: "bg-transparent text-muted-foreground border-border",
  };
  return (
    <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium border", styles[variant], className)}>
      {children}
    </span>
  );
}

export type BtnVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
export type BtnSize = "sm" | "md" | "lg";

export interface BtnProps {
  children?: React.ReactNode;
  onClick?: () => void;
  variant?: BtnVariant;
  size?: BtnSize;
  className?: string;
  disabled?: boolean;
  icon?: React.ReactNode;
}

export function Btn({ children, onClick, variant = "primary", size = "md", className, disabled, icon }: BtnProps) {
  const sizes: Record<BtnSize, string> = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" };
  const variants: Record<BtnVariant, string> = {
    primary: "bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/20",
    secondary: "bg-secondary text-foreground hover:bg-secondary/80 border border-border",
    ghost: "bg-transparent text-muted-foreground hover:bg-secondary hover:text-foreground",
    danger: "bg-destructive text-white hover:bg-destructive/90",
    outline: "bg-transparent border border-border text-foreground hover:bg-secondary",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cn("inline-flex items-center gap-2 rounded-lg font-medium transition-all duration-150 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed", sizes[size], variants[variant], className)}
    >
      {icon && icon}
      {children}
    </button>
  );
}

export interface InputProps {
  id?: string;
  placeholder?: string;
  value?: string;
  onChange?: (v: string) => void;
  type?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function Input({ id, placeholder, value, onChange, type = "text", icon, className, autoComplete = "off" }: InputProps & { autoComplete?: string }) {
  return (
    <div className={cn("relative", className)}>
      {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</div>}
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange?.(e.target.value)}
        className={cn(
          "w-full bg-input-background border border-border rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 transition-all",
          icon ? "pl-9 pr-3 py-2" : "px-3 py-2"
        )}
      />
    </div>
  );
}

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  onClick?: () => void;
}

export function Card({ children, className, onClick }: CardProps) {
  return (
    <div
      onClick={onClick}
      className={cn("bg-card border border-border rounded-xl", onClick && "cursor-pointer hover:border-primary/30 transition-all", className)}
    >
      {children}
    </div>
  );
}

export type ModalSize = "sm" | "md" | "lg";

export interface ModalProps {
  title: string;
  children: React.ReactNode;
  onClose: () => void;
  size?: ModalSize;
}

export function Modal({ title, children, onClose, size = "md" }: ModalProps) {
  const widths: Record<ModalSize, string> = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl" };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className={cn("relative bg-card border border-border rounded-2xl shadow-2xl w-full mx-4", widths[size])} onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="font-semibold text-foreground">{title}</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"><X size={18} /></button>
        </div>
        <div className="p-6">{children}</div>
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

export interface SparklineProps {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
}

export function Sparkline({ data, color = "#3B82F6", width = 80, height = 28 }: SparklineProps) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * width;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg width={width} height={height} className="overflow-visible">
      <polyline points={pts.join(" ")} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export const UI = {
  cn,
  getHypeColor,
  getEvidenceColor,
  ScorePill,
  Badge,
  Btn,
  Input,
  Card,
  Modal,
  HypeEvidenceBar,
  Sparkline,
};

export default UI;
