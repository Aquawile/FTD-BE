import { useEffect, useId, useRef } from "react";
import { X, FileText, Bell, Target, TrendingUp, TrendingDown } from "lucide-react";

export { X, FileText, Bell, Target, TrendingUp, TrendingDown };

export function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(" ");
}

/** Avatar letters: first letters of the first two words, or the first two letters of a single word. */
export function initialsOf(name: string | undefined | null, fallback = "??") {
  const words = (name || "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return fallback;
  return (words.length === 1 ? words[0].slice(0, 2) : words[0][0] + words[1][0]).toUpperCase();
}

export type BadgeVariant = "default" | "success" | "warning" | "neutral" | "danger" | "purple" | "outline";

export interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

export function Badge({ children, variant = "default", className }: BadgeProps) {
  const styles: Record<BadgeVariant, string> = {
    default: "bg-primary/15 text-primary border-primary/20",
    success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    warning: "bg-orange-500/10 text-orange-400 border-orange-500/20",
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
  ariaLabel?: string;
  autoComplete?: string;
  onEnter?: () => void;
}

export function Input({ id, placeholder, value, onChange, type = "text", icon, className, ariaLabel, autoComplete, onEnter }: InputProps) {
  return (
    <div className={cn("relative", className)}>
      {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</div>}
      <input
        id={id}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={e => onChange?.(e.target.value)}
        aria-label={ariaLabel}
        autoComplete={autoComplete}
        onKeyDown={onEnter ? e => { if (e.key === "Enter") { e.preventDefault(); onEnter(); } } : undefined}
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
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    // Escape closes the dialog; focus moves into it (unless a field inside already took focus) and returns afterwards.
    const previous = document.activeElement as HTMLElement | null;
    if (!dialogRef.current?.contains(document.activeElement)) dialogRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onCloseRef.current(); };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); previous?.focus?.(); };
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className={cn("relative bg-card border border-border rounded-2xl shadow-2xl w-full mx-4 focus:outline-none", widths[size])}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 id={titleId} className="font-semibold text-foreground">{title}</h3>
          <button onClick={onClose} aria-label="Close dialog" className="text-muted-foreground hover:text-foreground transition-colors cursor-pointer"><X size={18} /></button>
        </div>
        <div className="p-6">{children}</div>
      </div>
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
  Badge,
  Btn,
  Input,
  Card,
  Modal,
  Sparkline,
};

export default UI;
