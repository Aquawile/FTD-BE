import { useState, useRef, useEffect } from "react";
import {
  Search, Bell, Settings, LogOut, Home, Briefcase,
  MessageSquare, Clock, BarChart2, AlertTriangle,
  ChevronRight, ChevronDown, ChevronUp, TrendingUp,
  TrendingDown, Flag, X, Plus, FileText, Users,
  Shield, Activity, Download, Filter, ArrowRight,
  Check, Mail, Lock, Eye, EyeOff, Star, ExternalLink,
  RefreshCw, AlertCircle, CheckCircle, Info,
  MoreVertical, Edit2, Trash2, Archive,
  Database, Cpu, Globe, Zap, Target, PieChart,
  ChevronLeft, Menu, Layers, BookOpen, Send,
  Sparkles, BarChart, LineChart, Radio, Hash,
  Calendar, User, UserCheck, XCircle, Copy,
  ThumbsUp, ThumbsDown, Minus, Maximize2
} from "lucide-react";
import { initializeApp } from "firebase/app";
import { getAuth, signInWithEmailAndPassword, signOut, onAuthStateChanged, createUserWithEmailAndPassword, sendEmailVerification, User as FirebaseUser } from "firebase/auth";

const firebaseConfig = {
  projectId: "ftd-2026",
  apiKey: "AIzaSyA7CWNGUFkNYt9pbRF8Hh-l9lKJWSPnoQ8",
};

const firebaseApp = initializeApp(firebaseConfig);
const firebaseAuth = getAuth(firebaseApp);

const API_BASE = "/api";

async function apiRequest(path: string, firebaseUser: FirebaseUser | null): Promise<Response> {
  const headers: Record<string, string> = {};
  if (firebaseUser) {
    const token = await firebaseUser.getIdToken();
    headers["Authorization"] = `Bearer ${token}`;
  }
  return fetch(`${API_BASE}${path}`, { headers });
}

// ────────────────────────────────────────────────
// Types
// ────────────────────────────────────────────────
type Page =
  | "login" | "register" | "verify-email" | "forgot-password" | "onboarding-done"
  | "dashboard" | "search" | "ticker" | "ticker-timeline" | "ticker-filings" | "ticker-community" | "ticker-comparison"
  | "workspaces" | "workspace-detail" | "workspace-settings"
  | "chat" | "alerts" | "profile"
  | "admin" | "admin-mapping" | "admin-users" | "admin-system";

// ────────────────────────────────────────────────
// Mock Data (PRESERVED — not rendered in active UI)
// ────────────────────────────────────────────────
const TICKERS = [
  { symbol: "NVDA", name: "NVIDIA Corporation", hype: 84, evidence: 71, sector: "Semiconductors", change: +4.2, price: 873.50 },
  { symbol: "TSLA", name: "Tesla, Inc.", hype: 91, evidence: 48, sector: "Automotive / EV", change: -1.8, price: 243.20 },
  { symbol: "AAPL", name: "Apple Inc.", hype: 62, evidence: 88, sector: "Consumer Electronics", change: +0.9, price: 192.35 },
  { symbol: "MSFT", name: "Microsoft Corporation", hype: 58, evidence: 85, sector: "Cloud / AI", change: +1.4, price: 415.10 },
  { symbol: "AMD", name: "Advanced Micro Devices", hype: 76, evidence: 65, sector: "Semiconductors", change: +2.1, price: 162.40 },
  { symbol: "PLTR", name: "Palantir Technologies", hype: 88, evidence: 52, sector: "AI / Defense", change: -0.5, price: 24.80 },
  { symbol: "META", name: "Meta Platforms", hype: 67, evidence: 73, sector: "Social / AI", change: +3.1, price: 487.60 },
  { symbol: "GOOG", name: "Alphabet Inc.", hype: 61, evidence: 80, sector: "Search / Cloud", change: +1.2, price: 174.90 },
];

const NEWS_ARTICLES = [
  {
    id: 1, ticker: "NVDA",
    headline: "NVIDIA Announces Blackwell B200 GPU Mass Production Scale-Up Ahead of Schedule",
    source: "Reuters", time: "2h ago",
    hype: 78, evidence: 82,
    summary: "NVIDIA confirmed Blackwell GPU production ramp at TSMC is exceeding initial targets, with data center customers citing 6–8 week lead time improvements.",
    claims: ["Production 18% ahead of schedule", "TSMC yield rates improved to 94%", "Enterprise backlog exceeds $40B"],
    evidenceLinks: ["Q1 2024 10-Q Filing", "TSMC Supply Chain Report"],
    flagged: false,
  },
  {
    id: 2, ticker: "NVDA",
    headline: "Analysts Predict NVDA Will Reach $1,200 on 'Insatiable' AI Demand",
    source: "Seeking Alpha", time: "5h ago",
    hype: 91, evidence: 34,
    summary: "Multiple sell-side analysts raised price targets citing AI compute infrastructure expansion, though many projections lack specific customer commitment data.",
    claims: ["$1,200 PT within 12 months", "AI capex doubling in 2025", "No competitor for 3 years"],
    evidenceLinks: [],
    flagged: false,
  },
  {
    id: 3, ticker: "NVDA",
    headline: "SEC 10-K Filing: NVIDIA Discloses $18.4B Data Center Revenue, 427% YoY Growth",
    source: "SEC EDGAR", time: "1d ago",
    hype: 42, evidence: 97,
    summary: "Official SEC filing confirms record data center segment performance with detailed revenue breakdowns by geography and product line.",
    claims: ["$18.4B data center revenue", "427% YoY growth", "Gross margin 78.4%"],
    evidenceLinks: ["10-K Annual Report CY2024", "XBRL Financial Data"],
    flagged: false,
  },
  {
    id: 4, ticker: "NVDA",
    headline: "r/wallstreetbets: NVDA to $2000 — AI is bigger than the Internet",
    source: "Reddit WSB", time: "3h ago",
    hype: 97, evidence: 8,
    summary: "High-engagement WSB thread with 4.2K upvotes comparing NVIDIA's position to early Microsoft, citing speculative projections without financial disclosures.",
    claims: ["$2000 price target", "Bigger than internet revolution", "Buy now or regret forever"],
    evidenceLinks: [],
    flagged: false,
  },
];

const TIMELINE_EVENTS = [
  { date: "Jun 18, 2024", type: "filing", title: "10-Q Filed with SEC", description: "Quarterly filing confirms $26B revenue guidance raised by 12%.", score_delta: +8, hype: 45, evidence: 94 },
  { date: "Jun 15, 2024", type: "narrative", title: "Narrative Shift: Demand Concerns Resurface", description: "Multiple analyst notes cite potential hyperscaler capex pullback. Community sentiment shifted -14 points.", score_delta: -14, hype: 72, evidence: 60 },
  { date: "Jun 10, 2024", type: "news", title: "Product Launch: Blackwell B200 GA Confirmed", description: "Official press release from NVIDIA Investor Relations confirms general availability timeline.", score_delta: +12, hype: 65, evidence: 88 },
  { date: "May 28, 2024", type: "social", title: "Reddit Surge: +340% Post Volume", description: "WSB and r/stocks saw explosive discussion around NVDA options activity.", score_delta: +19, hype: 89, evidence: 41 },
  { date: "May 22, 2024", type: "earnings", title: "Q1 FY2025 Earnings Beat", description: "EPS of $6.12 vs $5.65 expected. Revenue $26.04B vs $24.6B estimate.", score_delta: +22, hype: 61, evidence: 96 },
  { date: "May 15, 2024", type: "news", title: "Microsoft Azure Partnership Expanded", description: "MSFT confirms multi-year GPU cluster commitment — undisclosed dollar value.", score_delta: +6, hype: 70, evidence: 62 },
  { date: "May 8, 2024", type: "social", title: "Hype Spike: AMD Competition Dismissed", description: "Community posts claim AMD MI300X is 'irrelevant' — limited technical evidence cited.", score_delta: +11, hype: 88, evidence: 29 },
  { date: "Apr 30, 2024", type: "filing", title: "8-K Filed: Executive Compensation Update", description: "CEO Jensen Huang RSU grant disclosed. No material business updates.", score_delta: 0, hype: 40, evidence: 85 },
];

const WORKSPACES = [
  { id: "ws1", name: "AI Semiconductor Race", tickers: ["NVDA", "AMD", "INTC", "TSM"], created: "Jun 1, 2024", alerts: 3 },
  { id: "ws2", name: "EV & Clean Energy", tickers: ["TSLA", "RIVN", "NIO", "ENPH", "FSLR"], created: "May 14, 2024", alerts: 1 },
  { id: "ws3", name: "Cloud Hyperscalers", tickers: ["MSFT", "AMZN", "GOOG", "META"], created: "Apr 22, 2024", alerts: 0 },
];

const MAPPING_QUEUE = [
  { id: "m1", article: "Tesla Releases FSD v13 Beta to 400K Users", mapped: "RIVN", suggested: "TSLA", source: "TechCrunch", confidence: 0.42, reporter: "user", time: "1h ago", type: "Wrong Ticker" },
  { id: "m2", article: "NVIDIA Supplier TSMC Sees Record Orders", mapped: "TSM", suggested: "NVDA", source: "Bloomberg", confidence: 0.61, reporter: "auto", time: "3h ago", type: "Ambiguous" },
  { id: "m3", article: "Palantir Wins $250M DoD Contract for AIP Platform", mapped: "PLTR", suggested: "PLTR", source: "Reuters", confidence: 0.88, reporter: "user", time: "6h ago", type: "Verify" },
  { id: "m4", article: "Apple Vision Pro Sales Miss Analyst Estimates", mapped: "META", suggested: "AAPL", source: "WSJ", confidence: 0.29, reporter: "auto", time: "2d ago", type: "Wrong Ticker" },
  { id: "m5", article: "AMD MI300X Outperforms H100 on LLM Inference Benchmarks", mapped: "AMD", suggested: "AMD", source: "AnandTech", confidence: 0.91, reporter: "auto", time: "3d ago", type: "Verify" },
];

const CHAT_HISTORY = [
  {
    role: "user",
    text: "Compare the evidence behind autonomous driving claims from Tesla vs Waymo",
    time: "10:42 AM",
  },
  {
    role: "ai",
    text: `**Multi-ticker analysis complete.** I searched across news, SEC filings, and community data for both **TSLA** and **Waymo (GOOGL)**.\n\n**Tesla FSD:**\n- Hype Score: 88/100 | Evidence Score: 52/100\n- Key claims in media: "Full autonomy by Q4 2024" — *No SEC filing corroboration found*\n- NHTSA open investigations: 4 active\n- Community sentiment: Highly polarized, 62% bullish\n\n**Waymo:**\n- Hype Score: 64/100 | Evidence Score: 79/100\n- Key claims: "6M+ robotaxi miles logged" — *Corroborated by Google Q1 2024 10-Q disclosure*\n- Regulatory approvals: California, Arizona commercial ops confirmed\n\n**Verdict:** Waymo carries significantly stronger evidence support for its autonomy claims. Tesla's claims outpace disclosed technical milestones by a wide margin.`,
    time: "10:42 AM",
    sources: ["TSLA 10-K 2023", "GOOGL Q1 2024 10-Q", "NHTSA Database", "r/RealTesla analysis"],
  },
  {
    role: "user",
    text: "What specific XBRL financial metrics does Tesla disclose for FSD revenue?",
    time: "10:44 AM",
  },
  {
    role: "ai",
    text: `**SEC Filing Analysis for TSLA — FSD Revenue Disclosure:**\n\nTesla classifies FSD revenue under **Automotive regulatory credits and deferred revenue** (ASC 606). Key XBRL metrics found:\n\n- Deferred revenue (FSD-related): $1.2B as of Q4 2023\n- Revenue recognized from FSD subscriptions: $326M (FY2023)\n- Subscription ARPU: ~$199/month (undisclosed in filing, derived)\n\n**Caution:** Tesla does not break out FSD separately in all filings. The $326M figure is extracted from narrative disclosure in Note 2, not a tagged XBRL element — making automated extraction unreliable.\n\n*Sources: TSLA 10-K FY2023 (Filed Feb 26, 2024), SEC EDGAR XBRL viewer*`,
    time: "10:44 AM",
    sources: ["TSLA 10-K FY2023", "SEC XBRL Data"],
  },
];

const ALERTS_DATA = [
  { id: "a1", ticker: "NVDA", type: "narrative_shift", message: "Hype/Evidence score delta exceeded +10 threshold", time: "2h ago", read: false, severity: "high" },
  { id: "a2", ticker: "TSLA", type: "filing", message: "New SEC 8-K filing detected — executive compensation update", time: "5h ago", read: false, severity: "medium" },
  { id: "a3", ticker: "AMD", type: "narrative_shift", message: "Community sentiment reversed — net negative shift detected", time: "1d ago", read: true, severity: "medium" },
  { id: "a4", ticker: "PLTR", type: "hype_spike", message: "Reddit post volume +280% in 4 hours — hype score elevated", time: "2d ago", read: true, severity: "low" },
  { id: "a5", ticker: "NVDA", type: "filing", message: "Q1 FY2025 10-Q filed with SEC EDGAR", time: "3d ago", read: true, severity: "medium" },
];

// ────────────────────────────────────────────────
// API Response Types
// ────────────────────────────────────────────────
interface TickerHeaderInfo {
  symbol: string;
  name: string;
  sector: string | null;
  price: number | null;
  evidence: number;
  hype: number;
  change: number;
}

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
interface WorkspaceInfo {
  id: number;
  name: string;
  tickers: string[];
  alerts: number;
  created_at: string | null;
}

interface AlertInfo {
  id: number;
  ticker: string | null;
  type: string;
  message: string;
  read: boolean;
  severity: string;
  time: string | null;
}

// ────────────────────────────────────────────────
// Utilities & Shared Components
// ────────────────────────────────────────────────
function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(" ");
}

function getHypeColor(score: number): string {
  if (score >= 80) return "#F97316";
  if (score >= 60) return "#F59E0B";
  if (score >= 40) return "#EAB308";
  return "#10B981";
}

function getEvidenceColor(score: number): string {
  if (score >= 80) return "#10B981";
  if (score >= 60) return "#34D399";
  if (score >= 40) return "#6EE7B7";
  return "#F97316";
}

function ScorePill({ label, score, type }: { label: string; score: number; type: "hype" | "evidence" }) {
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

function Badge({ children, variant = "default", className }: { children: React.ReactNode; variant?: "default" | "evidence" | "hype" | "neutral" | "danger" | "purple" | "outline"; className?: string }) {
  const styles = {
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

function Btn({ children, onClick, variant = "primary", size = "md", className, disabled, icon }: {
  children?: React.ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost" | "danger" | "outline";
  size?: "sm" | "md" | "lg"; className?: string; disabled?: boolean; icon?: React.ReactNode;
}) {
  const sizes = { sm: "px-3 py-1.5 text-xs", md: "px-4 py-2 text-sm", lg: "px-6 py-3 text-base" };
  const variants = {
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

function Input({ id, placeholder, value, onChange, type = "text", icon, className }: {
  id?: string; placeholder?: string; value?: string; onChange?: (v: string) => void; type?: string; icon?: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("relative", className)}>
      {icon && <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">{icon}</div>}
      <input
        id={id}
        type={type}
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

function Card({ children, className, onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) {
  return (
    <div
      onClick={onClick}
      className={cn("bg-card border border-border rounded-xl", onClick && "cursor-pointer hover:border-primary/30 transition-all", className)}
    >
      {children}
    </div>
  );
}

function Modal({ title, children, onClose, size = "md" }: { title: string; children: React.ReactNode; onClose: () => void; size?: "sm" | "md" | "lg" }) {
  const widths = { sm: "max-w-md", md: "max-w-lg", lg: "max-w-2xl" };
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

function HypeEvidenceBar({ hype, evidence, showLabels = true }: { hype: number; evidence: number; showLabels?: boolean }) {
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

// Mini sparkline using SVG
function Sparkline({ data, color = "#3B82F6", width = 80, height = 28 }: { data: number[]; color?: string; width?: number; height?: number }) {
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

// ────────────────────────────────────────────────
// Layout Shell
// ────────────────────────────────────────────────
function Sidebar({ page, navigate, collapsed, onCollapse }: {
  page: Page; navigate: (p: Page) => void; collapsed: boolean; onCollapse: () => void;
}) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Home },
    { id: "search", label: "Research", icon: Search },
    { id: "workspaces", label: "Workspaces", icon: Briefcase },
    { id: "ticker-timeline", label: "Timeline", icon: Clock },
    { id: "chat", label: "AI Assistant", icon: MessageSquare },
    { id: "alerts", label: "Alerts", icon: Bell },
    { id: "admin", label: "Admin", icon: Shield },
  ];
  return (
    <aside className={cn("flex flex-col h-screen sticky top-0 bg-sidebar border-r border-sidebar-border transition-all duration-200 shrink-0", collapsed ? "w-16" : "w-56")}>
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-sidebar-border">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
          <BarChart size={16} className="text-white" />
        </div>
        {!collapsed && <span className="font-bold text-foreground tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>}
        <button onClick={onCollapse} className={cn("ml-auto text-muted-foreground hover:text-foreground transition-colors cursor-pointer", collapsed && "mx-auto")}>
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 space-y-0.5 px-2">
        {navItems.map(item => {
          const Icon = item.icon;
          const active = page === item.id;
          return (
            <button
              key={item.id}
              onClick={() => navigate(item.id as Page)}
              className={cn(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all cursor-pointer",
                active ? "bg-sidebar-accent text-sidebar-accent-foreground font-medium" : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground"
              )}
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.id === "alerts" && <span className="ml-auto text-xs bg-orange-500 text-white rounded-full px-1.5 py-0.5 font-mono">2</span>}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-2 pb-4 space-y-0.5 border-t border-sidebar-border pt-3">
        <button onClick={() => navigate("profile")} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground transition-all cursor-pointer">
          <Settings size={16} className="shrink-0" />
          {!collapsed && <span>Settings</span>}
        </button>
      </div>
    </aside>
  );
}

function TopBar({ navigate, searchQuery, setSearchQuery, onSearch, unreadAlerts = 2, userEmail, userName, onSignOut }: {
  navigate: (p: Page) => void; searchQuery: string; setSearchQuery: (v: string) => void; onSearch: () => void; unreadAlerts?: number; userEmail?: string; userName?: string; onSignOut?: () => void;
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => { if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false); };
    const handleEscape = (e: KeyboardEvent) => { if (e.key === "Escape") setProfileOpen(false); };
    if (profileOpen) { document.addEventListener("mousedown", handleClickOutside); document.addEventListener("keydown", handleEscape); }
    return () => { document.removeEventListener("mousedown", handleClickOutside); document.removeEventListener("keydown", handleEscape); };
  }, [profileOpen]);
  return (
    <header className="sticky top-0 z-40 flex items-center gap-4 px-6 py-3 bg-background/95 backdrop-blur border-b border-border">
      <div className="relative flex-1 max-w-md">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search tickers, companies, topics..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && onSearch()}
          className="w-full bg-input-background border border-border rounded-lg pl-8 pr-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50"
        />
      </div>
      <div className="flex items-center gap-2 ml-auto">
        <button onClick={() => navigate("alerts")} className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-all cursor-pointer">
          <Bell size={18} />
          {unreadAlerts > 0 && <span className="absolute top-1 right-1 w-2 h-2 bg-orange-500 rounded-full" />}
        </button>
        <div className="relative" ref={profileRef}>
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white text-xs font-bold cursor-pointer" onClick={() => setProfileOpen(p => !p)}>
            {userName ? userName.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() : "IB"}
          </div>
          {profileOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-card border border-border rounded-xl shadow-lg py-2 z-50">
              <div className="px-4 py-2 border-b border-border/50">
                <div className="text-sm font-medium text-foreground truncate">{userName || "User"}</div>
                <div className="text-xs text-muted-foreground truncate">{userEmail || "user@example.com"}</div>
              </div>
              <button onClick={() => { setProfileOpen(false); navigate("profile"); }} className="w-full text-left px-4 py-2 text-sm text-foreground hover:bg-secondary transition-colors cursor-pointer">Profile</button>
              <button onClick={() => { setProfileOpen(false); onSignOut?.(); }} className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-secondary transition-colors cursor-pointer">Sign Out</button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

function AppShell({ page, navigate, children, userEmail, userName, onSignOut }: { page: Page; navigate: (p: Page) => void; children: React.ReactNode; userEmail?: string; userName?: string; onSignOut?: () => void }) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const handleSearch = () => { if (searchQuery.trim()) navigate("search"); };
  return (
    <div className="flex min-h-screen">
      <Sidebar page={page} navigate={navigate} collapsed={collapsed} onCollapse={() => setCollapsed(c => !c)} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar navigate={navigate} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onSearch={handleSearch} userEmail={userEmail} userName={userName} onSignOut={onSignOut} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 2: Login
// ────────────────────────────────────────────────
function LoginPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rememberMe, setRememberMe] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError("");
    try {
      await signInWithEmailAndPassword(firebaseAuth, email, password);
      navigate("profile");
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-gradient-to-br from-primary/10 to-secondary p-12 border-r border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
          <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
        </div>
        <div>
          <div className="text-4xl font-bold mb-4 leading-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Research with<br />
            <span style={{ color: "#10B981" }}>evidence.</span><br />
            Not noise.
          </div>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-sm">
            The platform that turns raw financial data into verifiable insight — with AI scoring every claim on an evidence scale.
          </p>
          <div className="mt-8 flex gap-4">
            {[{ n: "2.4M+", l: "Articles Analyzed" }, { n: "180K+", l: "Filings Indexed" }, { n: "94%", l: "Mapping Accuracy" }].map(s => (
              <div key={s.l}>
                <div className="font-mono font-bold text-lg text-primary">{s.n}</div>
                <div className="text-xs text-muted-foreground">{s.l}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="text-xs text-muted-foreground">Not investment advice · For research purposes only</div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-1">Welcome back</h1>
            <p className="text-muted-foreground text-sm">Sign in to your research account</p>
            <p className="text-sm text-muted-foreground mt-2">
              Don't have an account? <button onClick={() => navigate("register")} className="text-primary hover:underline cursor-pointer">Create one free</button>
            </p>
          </div>
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="login-email" className="text-sm font-medium">Email address</label>
                <Input id="login-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="login-password" className="text-sm font-medium">Password</label>
                  <div className="relative"><Input id="login-password" type={showPw ? "text" : "password"} value={password} onChange={setPassword} placeholder="Enter your password" icon={<Lock size={14} />} />
                <button onClick={() => setShowPw(p => !p)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer">
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" className="rounded" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} /> Remember me
              </label>
              <button onClick={() => navigate("forgot-password")} className="text-primary hover:underline cursor-pointer text-sm">Forgot password?</button>
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={handleLogin} disabled={loading}>
              {loading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
              {loading ? "Signing in..." : "Sign In"}
            </Btn>
          </div>
          <div className="relative"><div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div><div className="relative flex justify-center text-xs text-muted-foreground"><span className="bg-background px-3">or continue with</span></div></div>
          <Btn variant="outline" className="w-full justify-center" onClick={handleLogin}>
            <Globe size={14} /> Google
          </Btn>
          <p className="text-center text-sm text-muted-foreground">
            No account yet?{" "}
            <button onClick={() => navigate("register")} className="text-primary hover:underline cursor-pointer">Create one free</button>
          </p>
          {/* Admin shortcut */}
          <p className="text-center text-xs text-muted-foreground/50">
            <button onClick={() => { navigate("admin"); }} className="hover:text-muted-foreground cursor-pointer">Admin access →</button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 3: Register
// ────────────────────────────────────────────────
function RegisterPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const cred = await createUserWithEmailAndPassword(firebaseAuth, email, pw);
      await sendEmailVerification(cred.user);
      navigate("verify-email");
    } catch (err: any) {
      setError(err.message || "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-sm space-y-6">
        <button onClick={() => navigate("login")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back to sign in</button>
        <div>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <h1 className="text-2xl font-bold mb-1">Create your account</h1>
          <p className="text-muted-foreground text-sm">Free during beta · No credit card needed</p>
        </div>
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {error}
          </div>
        )}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="reg-email" className="text-sm font-medium">Email address</label>
            <Input id="reg-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="reg-password" className="text-sm font-medium">Password</label>
            <Input id="reg-password" type="password" value={pw} onChange={setPw} placeholder="Min. 8 characters" icon={<Lock size={14} />} />
          </div>
          {pw.length > 0 && (
            <div className="space-y-1">
              {[{ label: "8+ characters", ok: pw.length >= 8 }, { label: "Uppercase letter", ok: /[A-Z]/.test(pw) }, { label: "Number", ok: /[0-9]/.test(pw) }].map(r => (
                <div key={r.label} className="flex items-center gap-2 text-xs">
                  {r.ok ? <Check size={12} className="text-emerald-400" /> : <Minus size={12} className="text-muted-foreground" />}
                  <span className={r.ok ? "text-emerald-400" : "text-muted-foreground"}>{r.label}</span>
                </div>
              ))}
            </div>
          )}
          <Btn variant="primary" className="w-full justify-center" onClick={handleSubmit} disabled={!email || pw.length < 8 || loading}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <UserCheck size={14} />}
            {loading ? "Creating account..." : "Create Account"}
          </Btn>
        </div>
        <p className="text-center text-sm text-muted-foreground">Already have an account? <button onClick={() => navigate("login")} className="text-primary hover:underline cursor-pointer">Sign in</button></p>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 4: Verify Email
// ────────────────────────────────────────────────
function VerifyEmailPage({ navigate, userEmail }: { navigate: (p: Page) => void; userEmail?: string }) {
  const [resent, setResent] = useState(false);
  const displayEmail = userEmail || firebaseAuth.currentUser?.email || "your email";
  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-sm text-center space-y-6">
        <div className="w-20 h-20 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto">
          <Mail size={36} className="text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-bold mb-2">Check your inbox</h1>
          <p className="text-muted-foreground text-sm leading-relaxed">
            We sent a verification link to <strong className="text-foreground">{displayEmail}</strong>. Click the link to activate your account.
          </p>
        </div>
        <div className="p-4 bg-secondary/50 rounded-xl border border-border text-left text-sm space-y-2">
          <div className="flex items-center gap-2"><CheckCircle size={14} className="text-emerald-400" /><span>Email sent successfully</span></div>
          <div className="flex items-center gap-2"><Info size={14} className="text-blue-400" /><span>Link expires in 24 hours</span></div>
          <div className="flex items-center gap-2"><AlertCircle size={14} className="text-orange-400" /><span>Check your spam folder if not received</span></div>
        </div>
        <Btn variant="primary" className="w-full justify-center" onClick={() => navigate("profile")}>
          <Check size={14} /> I verified my email
        </Btn>
        <button
          onClick={() => setResent(true)}
          className="text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          disabled={resent}
        >
          {resent ? <span className="text-emerald-400 flex items-center gap-1 justify-center"><Check size={12} /> Email resent!</span> : "Resend verification email"}
        </button>
        <button onClick={() => navigate("login")} className="text-sm text-muted-foreground hover:text-foreground cursor-pointer flex items-center gap-1 justify-center">
          <ChevronLeft size={14} /> Back to sign in
        </button>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 5: Forgot Password
// ────────────────────────────────────────────────
function ForgotPasswordPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-sm space-y-6">
        <button onClick={() => navigate("login")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back to sign in</button>
        {!sent ? (
          <>
            <div>
              <h1 className="text-2xl font-bold mb-1">Reset your password</h1>
              <p className="text-muted-foreground text-sm">Enter your email and we will send a reset link valid for 1 hour.</p>
            </div>
            <div className="space-y-1.5">
              <label htmlFor="forgot-email" className="text-sm font-medium">Email address</label>
              <Input id="forgot-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={() => setSent(true)} disabled={!email.includes("@")}>
              <Send size={14} /> Send Reset Link
            </Btn>
          </>
        ) : (
          <div className="text-center space-y-4">
            <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
              <CheckCircle size={28} className="text-emerald-400" />
            </div>
            <h2 className="text-xl font-bold">Reset link sent</h2>
            <p className="text-muted-foreground text-sm">Check <strong className="text-foreground">{email}</strong> for the password reset link.</p>
            <Btn variant="outline" className="w-full justify-center" onClick={() => navigate("login")}>Return to Sign In</Btn>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 6: Onboarding Complete
// ────────────────────────────────────────────────
function OnboardingPage({ navigate }: { navigate: (p: Page) => void }) {
  const [step, setStep] = useState(0);
  const steps = ["Welcome!", "Pick your interests", "Set up first workspace"];
  const sectors = ["Semiconductors", "AI/ML", "EV & Clean Energy", "Cloud Infrastructure", "Defense Tech", "Biotech", "Consumer Electronics", "Crypto/Blockchain"];
  const [selected, setSelected] = useState<string[]>([]);

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <span className="text-sm text-muted-foreground">{step + 1} / {steps.length}</span>
        </div>
        <div className="flex gap-2">
          {steps.map((_, i) => <div key={i} className={cn("flex-1 h-1 rounded-full", i <= step ? "bg-primary" : "bg-secondary")} />)}
        </div>
        {step === 0 && (
          <div className="text-center space-y-4 py-4">
            <div className="text-5xl">🎉</div>
            <h1 className="text-2xl font-bold">Account verified!</h1>
            <p className="text-muted-foreground text-sm">Welcome to FTD. Let us personalize your experience in 2 quick steps.</p>
            <Btn variant="primary" size="lg" className="w-full justify-center" onClick={() => setStep(1)}>Get Started <ArrowRight size={14} /></Btn>
          </div>
        )}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">What sectors interest you?</h2>
            <p className="text-muted-foreground text-sm">Select all that apply — we will prioritize research content accordingly.</p>
            <div className="flex flex-wrap gap-2">
              {sectors.map(s => (
                <button
                  key={s}
                  onClick={() => setSelected(sel => sel.includes(s) ? sel.filter(x => x !== s) : [...sel, s])}
                  className={cn("px-3 py-1.5 rounded-lg text-sm border transition-all cursor-pointer", selected.includes(s) ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}
                >
                  {s}
                </button>
              ))}
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={() => setStep(2)} disabled={selected.length === 0}>
              Continue ({selected.length} selected) <ArrowRight size={14} />
            </Btn>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Create your first workspace</h2>
            <p className="text-muted-foreground text-sm">Group related tickers to track them together. You can always add more later.</p>
            <div className="space-y-1.5">
              <label htmlFor="workspace-name" className="text-sm font-medium">Workspace name</label>
              <Input id="workspace-name" placeholder="e.g., AI Semiconductor Race" icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="workspace-tickers" className="text-sm font-medium">Add tickers (optional)</label>
              <Input id="workspace-tickers" placeholder="NVDA, AMD, TSLA..." icon={<Hash size={14} />} />
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={() => navigate("profile")}>
              <Check size={14} /> Finish Setup
            </Btn>
            <button onClick={() => navigate("profile")} className="w-full text-center text-sm text-muted-foreground hover:text-foreground cursor-pointer">Skip for now</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 7: Dashboard Home
// ────────────────────────────────────────────────
function DashboardPage({ navigate, setSelectedTicker, firebaseUser }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; firebaseUser: FirebaseUser | null }) {
  const [stats, setStats] = useState<{ articles_count: number; tickers_count: number; alerts_count: number; evidence_score: number | null } | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);

  const [trackedTickers, setTrackedTickers] = useState<TrackedTicker[]>([]);
  const [tickersLoading, setTickersLoading] = useState(false);
  const [tickersError, setTickersError] = useState(false);

  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [workspacesLoading, setWorkspacesLoading] = useState(false);
  const [workspacesError, setWorkspacesError] = useState(false);

  const [alerts, setAlerts] = useState<AlertInfo[]>([]);
  const [alertsLoading, setAlertsLoading] = useState(false);
  const [alertsError, setAlertsError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const fetchStats = async () => {
      try {
        const res = await fetch("/api/dashboard/stats");
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) { setStats(data); setStatsLoading(false); }
      } catch {
        if (!cancelled) { setStatsError(true); setStatsLoading(false); }
      }
    };
    fetchStats();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchTracked = async () => {
      setTickersLoading(true);
      try {
        const res = await apiRequest("/tickers/tracked?limit=5", firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) { setTrackedTickers(Array.isArray(data) ? data : []); setTickersLoading(false); }
      } catch {
        if (!cancelled) { setTickersError(true); setTickersLoading(false); }
      }
    };
    fetchTracked();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchWorkspaces = async () => {
      setWorkspacesLoading(true);
      try {
        const res = await apiRequest("/workspaces", firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) { setWorkspaces(Array.isArray(data) ? data : []); setWorkspacesLoading(false); }
      } catch {
        if (!cancelled) { setWorkspacesError(true); setWorkspacesLoading(false); }
      }
    };
    fetchWorkspaces();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchAlerts = async () => {
      setAlertsLoading(true);
      try {
        const res = await apiRequest("/alerts?limit=3", firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) { setAlerts(Array.isArray(data) ? data : []); setAlertsLoading(false); }
      } catch {
        if (!cancelled) { setAlertsError(true); setAlertsLoading(false); }
      }
    };
    fetchAlerts();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const formatCount = (n: number) => {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1).replace(/\.0$/, "") + "M";
    if (n >= 1_000) return (n / 1_000).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  };

  const spData = [45, 52, 48, 63, 71, 68, 74, 69, 77, 82, 79, 84];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Welcome */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Good morning 👋</h1>
        </div>
        <Btn variant="primary" onClick={() => navigate("chat")} icon={<MessageSquare size={14} />}>Ask AI</Btn>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {statsLoading ? (
          Array.from({ length: 2 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-6 bg-secondary rounded w-1/3" /></div></Card>
          ))
        ) : statsError ? (
          <Card className="p-4 col-span-full text-sm text-red-400">Unable to load dashboard stats</Card>
        ) : (
          <>
            <Card className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-muted-foreground text-xs mb-1">Articles Analyzed</div>
                  <div className="font-mono font-bold text-2xl text-foreground">{formatCount(stats?.articles_count ?? 0)}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Total in database</div>
                </div>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-emerald-500/10 text-emerald-400"><FileText size={18} /></div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-muted-foreground text-xs mb-1">Tickers Tracked</div>
                  <div className="font-mono font-bold text-2xl text-foreground">{formatCount(stats?.tickers_count ?? 0)}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">Across all sources</div>
                </div>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-blue-500/10 text-blue-400"><Target size={18} /></div>
              </div>
            </Card>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Movers */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-foreground">Top Hype/Evidence Divergence</h2>
            <button onClick={() => navigate("search")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
          </div>
          <Card>
            <div className="divide-y divide-border">
              {tickersLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4 p-4">
                    <div className="w-10 h-10 rounded-xl bg-secondary animate-pulse shrink-0" />
                    <div className="flex-1 space-y-1"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div>
                    <div className="text-right space-y-1"><div className="h-3 bg-secondary rounded w-12" /><div className="h-3 bg-secondary rounded w-10" /></div>
                  </div>
                ))
              ) : tickersError ? (
                <div className="p-4 text-center text-sm text-muted-foreground">Unable to load tracked tickers</div>
              ) : trackedTickers.length === 0 ? (
                <div className="p-4 text-center text-sm text-muted-foreground">No tickers being tracked yet</div>
              ) : (
                trackedTickers.map(t => (
                  <div
                    key={t.symbol}
                    className="flex items-center gap-4 p-4 hover:bg-secondary/30 cursor-pointer transition-all"
                    onClick={() => { setSelectedTicker(t.symbol); navigate("ticker"); }}
                  >
                    <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center shrink-0">
                      <span className="font-mono font-bold text-xs text-foreground">{t.symbol.slice(0, 2)}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-semibold text-sm text-foreground">{t.symbol}</span>
                        <span className="text-muted-foreground text-xs truncate">{t.name || t.sector}</span>
                      </div>
                      <div className="mt-1.5 flex items-center gap-3">
                        <div className="text-xs text-muted-foreground">
                          Price data available
                        </div>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="font-mono text-sm font-semibold text-foreground">${t.current_price?.toLocaleString() ?? "—"}</div>
                      <div className={cn("text-xs flex items-center gap-0.5 justify-end", (t.change_percent ?? 0) > 0 ? "text-emerald-400" : "text-red-400")}>
                        {(t.change_percent ?? 0) > 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                        {(t.change_percent ?? 0) > 0 ? "+" : ""}{t.change_percent ?? 0}%
                      </div>
                    </div>
                    <Sparkline data={spData.map(v => v + Math.random() * 8 - 4)} color={(t.change_percent ?? 0) > 0 ? "#10B981" : "#EF4444"} />
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Recent alerts */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-foreground">Recent Alerts</h2>
              <button onClick={() => navigate("alerts")} className="text-xs text-primary hover:underline cursor-pointer">All alerts →</button>
            </div>
            <div className="space-y-2">
              {alertsLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i} className="p-3"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
                ))
              ) : alertsError ? (
                <Card className="p-3 text-sm text-muted-foreground">Unable to load alerts</Card>
              ) : alerts.length === 0 ? (
                <Card className="p-3 text-sm text-muted-foreground">No alerts yet</Card>
              ) : (
                alerts.map(a => (
                  <Card key={a.id} className="p-3">
                    <div className="flex items-start gap-2">
                      <div className={cn("w-1.5 h-1.5 rounded-full mt-1.5 shrink-0", a.read ? "bg-secondary" : "bg-orange-400")} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1 mb-0.5">
                          <span className="font-mono font-semibold text-xs text-foreground">{a.ticker || "—"}</span>
                          <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.type.replace("_", " ")}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground leading-relaxed">{a.message}</p>
                        <div className="text-xs text-muted-foreground/60 mt-1">{a.time || ""}</div>
                      </div>
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>

          {/* Workspace quick view */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-semibold text-foreground">My Workspaces</h2>
              <button onClick={() => navigate("workspaces")} className="text-xs text-primary hover:underline cursor-pointer">Manage →</button>
            </div>
            <div className="space-y-2">
              {workspacesLoading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <Card key={i} className="p-3"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
                ))
              ) : workspacesError ? (
                <Card className="p-3 text-sm text-muted-foreground">Unable to load workspaces</Card>
              ) : workspaces.length === 0 ? (
                <Card className="p-3 text-sm text-muted-foreground cursor-pointer" onClick={() => navigate("workspaces")}>No workspaces yet — create one</Card>
              ) : (
                workspaces.map(ws => (
                  <Card key={ws.id} className="p-3 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("workspace-detail")}>
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-sm text-foreground">{ws.name}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{ws.tickers.join(", ")}</div>
                      </div>
                      {ws.alerts > 0 && <Badge variant="hype" className="text-xs">{ws.alerts}</Badge>}
                    </div>
                  </Card>
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI chat preview */}
      <Card className="p-5 border-primary/20 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
            <Sparkles size={18} className="text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-foreground">AI Research Assistant</h3>
            <p className="text-xs text-muted-foreground">Ask complex multi-ticker questions. Sources always cited.</p>
          </div>
          <Btn variant="primary" size="sm" onClick={() => navigate("chat")} icon={<MessageSquare size={12} />}>Open Chat</Btn>
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 8: Search Results
// ────────────────────────────────────────────────
function SearchPage({ navigate, setSelectedTicker, firebaseUser }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void; firebaseUser: FirebaseUser | null }) {
  const [query, setQuery] = useState("NVDA");
  const [filterSector, setFilterSector] = useState("all");
  const [sortBy, setSortBy] = useState("divergence");
  const [results, setResults] = useState<Array<{ ticker: string; cik: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!query.trim() || !firebaseUser) {
      setResults([]);
      return;
    }
    setLoading(true);
    setError(false);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    apiRequest(`${API_BASE}/tickers/search?q=${encodeURIComponent(query)}&limit=20`, firebaseUser)
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
  }, [query, firebaseUser]);

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
function TickerDashboard({ navigate, ticker, onReport, firebaseUser }: { navigate: (p: Page) => void; ticker: string; onReport: () => void; firebaseUser: FirebaseUser | null }) {
  const [tab, setTab] = useState("overview");
  const [articles, setArticles] = useState<Array<{
    id: number; headline: string; source: string; time: string;
    hype: number; evidence: number; summary: string; claims: string[];
    evidenceLinks: string[]; flagged: boolean;
  }>>([]);
  const [articlesLoading, setArticlesLoading] = useState(false);
  const [articlesError, setArticlesError] = useState(false);
  const [tickerData, setTickerData] = useState<TickerHeaderInfo | null>(null);
  const t = tickerData || TICKERS.find(t => t.symbol === ticker) || TICKERS[0];
  const tabs = ["overview", "news", "evidence", "community", "filings", "timeline"];

  const flagArticle = (id: number) => setArticles(prev => prev.map(a => a.id === id ? { ...a, flagged: !a.flagged } : a));

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchNews = async () => {
      if (!tickerData) {
        try {
          const trackedRes = await apiRequest(`${API_BASE}/tickers/tracked?limit=500`, firebaseUser);
          if (trackedRes.ok) {
            const trackedData = await trackedRes.json();
            const match = Array.isArray(trackedData) ? trackedData.find((t: any) => t.symbol === ticker) : null;
            if (match && !cancelled) setTickerData({
              symbol: match.symbol,
              name: match.name,
              sector: match.sector,
              price: match.current_price,
              evidence: match.evidence_score || 0,
              hype: match.hype_score || 0,
              change: match.change_percent || 0,
            });
          }
        } catch {}
      }
      setArticlesLoading(true);
      try {
        const end = new Date().toISOString().split("T")[0];
        const start = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
        const res = await apiRequest(`${API_BASE}/tickers/${ticker}/news?start=${start}&end=${end}&limit=10`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setArticles(Array.isArray(data) ? data.map((item: any, idx: number) => ({
            id: idx,
            headline: item.content_body || "",
            source: "News",
            time: item.normalized_calendar_date || "",
            hype: 0,
            evidence: 100,
            summary: item.content_body || "",
            claims: [],
            evidenceLinks: [],
            flagged: false,
          })) : []);
          setArticlesLoading(false);
        }
      } catch {
        if (!cancelled) { setArticlesError(true); setArticlesLoading(false); }
      }
    };
    if (tab === "news" || tab === "overview") {
      fetchNews();
    }
    return () => { cancelled = true; };
  }, [firebaseUser, ticker, tab]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-card border-b border-border px-6 py-5">
        <div className="flex items-start justify-between gap-4 max-w-7xl mx-auto">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center shrink-0">
              <span className="font-mono font-bold text-lg text-foreground">{t.symbol.slice(0, 2)}</span>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-2xl font-bold font-mono text-foreground">{t.symbol}</h1>
                <Badge variant="neutral">{t.sector}</Badge>
                <Badge variant="neutral">NASDAQ</Badge>
              </div>
              <div className="text-muted-foreground text-sm">{t.name}</div>
              <div className="flex items-center gap-4 mt-2">
                <span className="font-mono font-bold text-xl text-foreground">${t.price.toLocaleString()}</span>
                <span className={cn("flex items-center gap-1 text-sm", t.change > 0 ? "text-emerald-400" : "text-red-400")}>
                  {t.change > 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  {t.change > 0 ? "+" : ""}{t.change}%
                </span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="flex items-center gap-3">
              <Btn variant="secondary" size="sm" icon={<Bell size={12} />} onClick={() => navigate("alerts")}>Set Alert</Btn>
              <Btn variant="secondary" size="sm" icon={<Briefcase size={12} />} onClick={() => navigate("workspaces")}>Add to Workspace</Btn>
              <Btn variant="secondary" size="sm" icon={<Maximize2 size={12} />} onClick={() => navigate("ticker-comparison")}>Compare</Btn>
            </div>
            <div className="flex items-center gap-6">
              <ScorePill label="Hype Score" score={t.hype} type="hype" />
              <ScorePill label="Evidence Score" score={t.evidence} type="evidence" />
            </div>
          </div>
        </div>
        {/* Tabs */}
        <div className="flex gap-0 mt-5 max-w-7xl mx-auto border-b border-transparent -mb-5">
          {tabs.map(tab_ => (
            <button
              key={tab_}
              onClick={() => { if (tab_ === "timeline") navigate("ticker-timeline"); else if (tab_ === "filings") navigate("ticker-filings"); else if (tab_ === "community") navigate("ticker-community"); else setTab(tab_); }}
              className={cn(
                "px-4 py-2 text-sm border-b-2 transition-all cursor-pointer capitalize",
                tab === tab_ ? "border-primary text-primary font-medium" : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab_}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 max-w-7xl mx-auto w-full">
        {tab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Main col */}
            <div className="lg:col-span-2 space-y-5">
              {/* AI Summary */}
              <Card className="p-5 border-purple-500/20 bg-gradient-to-r from-primary/5 to-accent/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
                    <Sparkles size={18} className="text-purple-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-sm text-foreground">AI Research Summary</h3>
                    <p className="text-xs text-muted-foreground">Ask the AI assistant for a multi-ticker analysis</p>
                  </div>
                  <Btn variant="primary" size="sm" onClick={() => navigate("chat")} icon={<MessageSquare size={12} />}>Open Chat</Btn>
                </div>
              </Card>

              {/* Key claims */}
              <div>
                <h3 className="font-semibold mb-3">Key Claims in Circulation</h3>
                <div className="space-y-2">
                  {articlesLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-secondary/30 rounded-lg border border-border/50">
                        <div className="h-4 bg-secondary rounded w-full animate-pulse" />
                      </div>
                    ))
                  ) : articles.length === 0 ? (
                    <div className="text-sm text-muted-foreground">No claims data available yet.</div>
                  ) : (
                  articles.slice(0, 4).map((a, idx) => (
                    <div key={a.id || idx} className="flex items-start gap-3 p-3 bg-secondary/30 rounded-lg border border-border/50">
                      <div className="w-2 h-2 rounded-full mt-1.5 shrink-0 bg-blue-400" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-foreground">{a.headline || a.summary?.slice(0, 80) || "No headline available"}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{a.source} · {a.time}</div>
                      </div>
                      <Badge variant="neutral" className="shrink-0 text-xs capitalize">
                        unverified
                      </Badge>
                    </div>
                  ))
                  )}
                </div>
              </div>

              {/* Recent news */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">Recent News & Analysis</h3>
                  <button onClick={() => setTab("news")} className="text-xs text-primary hover:underline cursor-pointer">View all →</button>
                </div>
                <div className="space-y-3">
                  {articlesLoading ? (
                    Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="flex items-start gap-3 p-4 bg-secondary/30 rounded-xl border border-border/50 group">
                        <div className="flex-1 space-y-2"><div className="h-3 bg-secondary rounded w-3/4 animate-pulse" /><div className="h-3 bg-secondary rounded w-full animate-pulse" /></div>
                      </div>
                    ))
                  ) : articles.slice(0, 3).map(a => (
                    <div key={a.id} className="flex items-start gap-3 p-4 bg-secondary/30 rounded-xl border border-border/50 group">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs text-muted-foreground">{a.source}</span>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">{a.time}</span>
                        </div>
                        <div className="text-sm font-medium text-foreground leading-tight mb-2">{a.headline}</div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono" style={{ color: getHypeColor(a.hype) }}>H:{a.hype}</span>
                          <span className="text-xs font-mono" style={{ color: getEvidenceColor(a.evidence) }}>E:{a.evidence}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => { flagArticle(a.id); onReport(); }}
                        className={cn("p-1.5 rounded-lg border transition-all cursor-pointer opacity-0 group-hover:opacity-100", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400 opacity-100" : "border-border text-muted-foreground hover:border-orange-500/30 hover:text-orange-400")}
                        title="Report incorrect mapping"
                      >
                        <Flag size={12} />
                      </button>
                    </div>
                  ))}
            </div>

            {/* Sidebar */}
            <div className="space-y-4">
              {/* Financials */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Key Financials</h3>
                <div className="text-center py-6 text-muted-foreground text-xs">
                  Financial data will appear once ticker-level SEC data is loaded.
                </div>
              </Card>

              {/* Source breakdown */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Source Breakdown</h3>
                <div className="text-center py-6 text-muted-foreground text-xs">
                  Source-level scoring will appear once data is ingested.
                </div>
              </Card>

              {/* Quick actions */}
              <Card className="p-4">
                <h3 className="font-semibold text-sm mb-3">Quick Actions</h3>
                <div className="space-y-1.5">
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Clock size={12} />} onClick={() => navigate("ticker-timeline")}>View Timeline</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<FileText size={12} />} onClick={() => navigate("ticker-filings")}>SEC Filings</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Users size={12} />} onClick={() => navigate("ticker-community")}>Community Sentiment</Btn>
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-timeline")}>Export Report</Btn>
                </div>
              </Card>
            </div>
          </div>
        )}

        {tab === "news" && (
          <div className="space-y-3">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex gap-2">
                {["all", "news", "analysis", "reddit"].map(f => (
                  <button key={f} className="px-3 py-1 rounded-lg text-xs border border-border bg-secondary text-muted-foreground hover:text-foreground cursor-pointer capitalize">{f}</button>
                ))}
              </div>
              <div className="ml-auto text-xs text-muted-foreground">{articles.length} articles</div>
            </div>
            {articlesLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <Card key={i} className="p-5"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
              ))
            ) : articlesError ? (
              <Card className="p-4 text-sm text-muted-foreground">Unable to load articles</Card>
            ) : articles.length === 0 ? (
              <Card className="p-4 text-sm text-muted-foreground">No news articles available</Card>
            ) : (
            articles.map(a => (
              <Card key={a.id} className="p-5">
                <div className="flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="neutral" className="text-xs">{a.source}</Badge>
                      <span className="text-xs text-muted-foreground">{a.time}</span>
                      {a.flagged && <Badge variant="hype" className="text-xs"><Flag size={8} /> Reported</Badge>}
                    </div>
                    <h4 className="font-semibold text-sm text-foreground mb-2 leading-snug">{a.headline}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">{a.summary}</p>
                    {a.claims.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {a.claims.map(c => <Badge key={c} variant="outline" className="text-xs">{c}</Badge>)}
                      </div>
                    )}
                    {a.evidenceLinks.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {a.evidenceLinks.map(l => <Badge key={l} variant="evidence" className="text-xs"><ExternalLink size={8} /> {l}</Badge>)}
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <div className="text-right space-y-1">
                      <div className="text-xs text-muted-foreground">Hype</div>
                      <div className="font-mono text-sm font-bold" style={{ color: getHypeColor(a.hype) }}>{a.hype}</div>
                    </div>
                    <div className="text-right space-y-1">
                      <div className="text-xs text-muted-foreground">Evidence</div>
                      <div className="font-mono text-sm font-bold" style={{ color: getEvidenceColor(a.evidence) }}>{a.evidence}</div>
                    </div>
                    <button
                      onClick={() => { flagArticle(a.id); onReport(); }}
                      className={cn("mt-2 p-2 rounded-lg border transition-all cursor-pointer", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400" : "border-border text-muted-foreground hover:text-orange-400 hover:border-orange-500/30")}
                    >
                      <Flag size={13} />
                    </button>
                  </div>
                </div>
              </Card>
            ))
            )}
          </div>
        )}

        {tab === "evidence" && (
          <div className="space-y-5">
            <Card className="p-5">
              <h3 className="font-semibold mb-4">Evidence Breakdown Matrix</h3>
              <div className="space-y-4">
                {[
                  { category: "SEC Filings & XBRL Data", score: 94, count: "12 filings", description: "All major financial disclosures verified and parsed. Revenue, margin, and segment data fully corroborated." },
                  { category: "Analyst Reports", score: 72, count: "28 reports", description: "Sell-side consensus moderately evidenced. Price targets range 20–150% above current price with mixed backing." },
                  { category: "News Articles", score: 61, count: "847 articles", description: "Mainstream financial news mostly factual with selective embellishment in headlines." },
                  { category: "Community / Reddit", score: 23, count: "2,341 posts", description: "Heavy speculative content. Most high-engagement posts lack quantitative financial evidence." },
                ].map(e => (
                  <div key={e.category} className="p-4 bg-secondary/30 rounded-xl border border-border/50">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium text-sm text-foreground">{e.category}</span>
                        <span className="text-xs text-muted-foreground ml-2">{e.count}</span>
                      </div>
                      <span className="font-mono font-bold text-sm" style={{ color: getEvidenceColor(e.score) }}>{e.score}/100</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden mb-2">
                      <div className="h-full rounded-full transition-all" style={{ width: `${e.score}%`, background: getEvidenceColor(e.score) }} />
                    </div>
                    <p className="text-xs text-muted-foreground">{e.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 10: Narrative Timeline
// ────────────────────────────────────────────────
function TimelinePage({ navigate, ticker, firebaseUser }: { navigate: (p: Page) => void; ticker: string; firebaseUser: FirebaseUser | null }) {
  const [showExport, setShowExport] = useState(false);
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const typeColors: Record<string, string> = {
    filing: "#10B981", narrative: "#F59E0B", news: "#3B82F6", social: "#F97316", earnings: "#8B5CF6",
  };
  const typeIcons: Record<string, React.ReactNode> = {
    filing: <FileText size={12} />, narrative: <Activity size={12} />, news: <Globe size={12} />, social: <Users size={12} />, earnings: <BarChart2 size={12} />,
  };

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchTimeline = async () => {
      setLoading(true);
      try {
        const end = new Date().toISOString().split("T")[0];
        const start = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
        const res = await apiRequest(`${API_BASE}/tickers/${ticker}/timeline?start=${start}&end=${end}&sources=finnhub,gnews,sec&limit=100`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setEvents(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    };
    fetchTimeline();
    return () => { cancelled = true; };
  }, [firebaseUser, ticker]);

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
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="relative flex gap-5 pl-8">
                <div className="absolute left-0 top-3 w-8 h-8 rounded-full animate-pulse bg-secondary shrink-0" />
                <Card className="flex-1 p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
              </div>
            ))
          ) : error ? (
            <div className="text-center py-8 text-muted-foreground">
              <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
              <p>Unable to load timeline data</p>
            </div>
          ) : events.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Clock size={32} className="mx-auto mb-2 opacity-50" />
              <p>No timeline events available</p>
            </div>
          ) : (
          events.map((ev, i) => (
            <div key={i} className="relative flex gap-5 pl-8">
              <div className="absolute left-0 top-3 w-8 h-8 rounded-full flex items-center justify-center border-2 border-background" style={{ background: typeColors[ev.source] || "#3B82F6" }}>
                <span style={{ color: "#fff" }}>{typeIcons[ev.source] || <Globe size={12} />}</span>
              </div>
              <Card className="flex-1 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge className="text-xs capitalize" style={{ background: `${typeColors[ev.source] || "#3B82F6"}15`, color: typeColors[ev.source] || "#3B82F6", borderColor: `${typeColors[ev.source] || "#3B82F6"}30` }}>{ev.source || "unknown"}</Badge>
                      <span className="text-xs text-muted-foreground">{ev.normalized_calendar_date || ev.ingest_date || ""}</span>
                    </div>
                    <h4 className="font-medium text-sm text-foreground mb-1">{ev.element_type || ev.content_body?.slice(0, 100) || "No title"}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed">{ev.content_body?.slice(0, 200) || "No description available"}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs font-mono font-semibold text-muted-foreground">
                      {ev.form_type || "—"}
                    </div>
                    <div className="text-xs text-muted-foreground">type</div>
                  </div>
                </div>
              </Card>
            </div>
          ))
          )}
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
function FilingsPage({ navigate, ticker, firebaseUser }: { navigate: (p: Page) => void; ticker: string; firebaseUser: FirebaseUser | null }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [filings, setFilings] = useState<Array<{
    target_ticker: string; target_cik: string; form_type: string;
    accession_number: string; filing_date: string | null; element_count: number;
  }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchFilings = async () => {
      setLoading(true);
      try {
        const res = await apiRequest(`${API_BASE}/tickers/${ticker}/filings`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setFilings(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    };
    fetchFilings();
    return () => { cancelled = true; };
  }, [firebaseUser, ticker]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer">
          <ChevronLeft size={14} /> {ticker}
        </button>
        <h1 className="text-xl font-bold flex-1">SEC Filings — {ticker}</h1>
        <Badge variant="evidence"><CheckCircle size={10} /> EDGAR Verified</Badge>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2 space-y-2">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
            ))
          ) : error ? (
            <Card className="p-4 text-sm text-muted-foreground">Unable to load filings</Card>
          ) : filings.length === 0 ? (
            <Card className="p-4 text-sm text-muted-foreground">No filings found for {ticker}</Card>
          ) : (
          filings.map(f => (
            <Card key={f.accession_number || f.form_type} className={cn("p-4 cursor-pointer transition-all", selected === f.accession_number ? "border-primary/50 bg-primary/5" : "hover:border-primary/20")} onClick={() => setSelected(selected === f.accession_number ? null : f.accession_number)}>
              <div className="flex items-start gap-3">
                <div className={cn("px-2 py-0.5 rounded text-xs font-mono font-bold", f.form_type === "10-K" ? "bg-emerald-500/15 text-emerald-400" : f.form_type === "10-Q" ? "bg-blue-500/15 text-blue-400" : "bg-orange-500/15 text-orange-400")}>
                  {f.form_type}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm text-foreground">{f.accession_number?.slice(0, 20) || "N/A"}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{f.filing_date ? new Date(f.filing_date).toLocaleDateString() : "—"} · {f.element_count} elements</div>
                </div>
                <ChevronRight size={14} className="text-muted-foreground shrink-0" />
              </div>
            </Card>
          ))
          )}
        </div>
        <div className="lg:col-span-3">
          {selected ? (
            <Card className="p-5 sticky top-0">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="font-semibold">Filing Analysis</h3>
                  <p className="text-xs text-muted-foreground">Accession: {selected}</p>
                </div>
                <Btn variant="secondary" size="sm" icon={<ExternalLink size={12} />}>View on EDGAR</Btn>
              </div>
              <div className="text-center py-12 text-muted-foreground text-sm">
                <FileText size={32} className="mx-auto mb-2 opacity-30" />
                <p>Select a filing to view analysis. Click on any section name in the left list to begin.</p>
              </div>
            </Card>
          ) : (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              <div className="text-center">
                <FileText size={32} className="mx-auto mb-2 opacity-30" />
                <p>Select a filing to view analysis</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 12: Community Sentiment
// ────────────────────────────────────────────────
function CommunityPage({ navigate, ticker }: { navigate: (p: Page) => void; ticker: string }) {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> {ticker}</button>
        <h1 className="text-xl font-bold flex-1">Community Sentiment — {ticker}</h1>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        <Card className="p-4 text-center">
          <div className="font-mono font-bold text-xl mb-1 text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">Total Posts (7d)</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="font-mono font-bold text-xl mb-1 text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">Avg Hype Score</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="font-mono font-bold text-xl mb-1 text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">Avg Evidence Score</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="font-mono font-bold text-xl mb-1 text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">Net Sentiment</div>
        </Card>
      </div>
      <Card className="p-6 text-center py-12">
        <Users size={32} className="mx-auto mb-2 opacity-20" />
        <p className="text-muted-foreground text-sm">No community posts available yet.</p>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 13: Ticker Comparison
// ────────────────────────────────────────────────
function ComparisonPage({ navigate, firebaseUser }: { navigate: (p: Page) => void; firebaseUser: FirebaseUser | null }) {
  const [tickers, setTickers] = useState<TrackedTicker[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchTickers = async () => {
      setLoading(true);
      try {
        const res = await apiRequest(`${API_BASE}/tickers/tracked?limit=10`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setTickers(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setLoading(false); }
      }
    };
    fetchTickers();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("dashboard")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Dashboard</button>
        <h1 className="text-xl font-bold flex-1">Multi-Ticker Comparison</h1>
        <Btn variant="secondary" size="sm" icon={<Plus size={12} />}>Add Ticker</Btn>
      </div>
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-3"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
          ))}
        </div>
      ) : tickers.length === 0 ? (
        <Card className="p-6 text-center py-12">
          <BarChart2 size={32} className="mx-auto mb-2 opacity-20" />
          <p className="text-muted-foreground text-sm">No tickers available for comparison. Track tickers from the dashboard.</p>
        </Card>
      ) : (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {tickers.slice(0, 3).map(t => (
          <div key={t.symbol} className="space-y-4">
            <Card className="p-4 border-t-2" style={{ borderTopColor: "#3B82F6" }}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-secondary flex items-center justify-center">
                  <span className="font-mono font-bold text-sm">{t.symbol.slice(0, 2)}</span>
                </div>
                <div>
                  <div className="font-mono font-bold text-foreground">{t.symbol}</div>
                  <div className="text-xs text-muted-foreground">{t.name || t.sector || ""}</div>
                </div>
              </div>
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Hype Score</span><span className="font-mono" style={{ color: getHypeColor(t.hype_score ?? 0) }}>{t.hype_score ?? 0}</span></div>
                  <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.hype_score ?? 0}%`, background: getHypeColor(t.hype_score ?? 0) }} /></div>
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1"><span className="text-muted-foreground">Evidence Score</span><span className="font-mono" style={{ color: getEvidenceColor(t.evidence_score ?? 0) }}>{t.evidence_score ?? 0}</span></div>
                  <div className="h-2 rounded-full bg-secondary overflow-hidden"><div className="h-full rounded-full" style={{ width: `${t.evidence_score ?? 0}%`, background: getEvidenceColor(t.evidence_score ?? 0) }} /></div>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground pt-1 border-t border-border">
                  <span>Gap (H-E)</span>
                  <span className={cn("font-mono", ((t.hype_score ?? 0) - (t.evidence_score ?? 0)) > 20 ? "text-orange-400" : "text-emerald-400")}>{((t.hype_score ?? 0) - (t.evidence_score ?? 0)) > 0 ? "+" : ""}{(t.hype_score ?? 0) - (t.evidence_score ?? 0)}</span>
                </div>
              </div>
            </Card>
            <Card className="p-4">
              <div className="space-y-2 text-xs">
                {[{ l: "Price", v: t.current_price ? `$${t.current_price}` : "—" }, { l: "24h Change", v: t.change_percent ? `${t.change_percent > 0 ? "+" : ""}${t.change_percent}%` : "—" }, { l: "Sector", v: t.sector || "—" }].map(r => (
                  <div key={r.l} className="flex justify-between"><span className="text-muted-foreground">{r.l}</span><span className="font-mono text-foreground">{r.v}</span></div>
                ))}
              </div>
            </Card>
            <Card className="p-4">
              <div className="text-xs font-semibold mb-2">AI Verdict</div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Comparative analysis will appear once the AI assistant has evaluated the available evidence for these tickers.
              </p>
            </Card>
          </div>
        ))}
      </div>
      )}
      <Card className="mt-6 p-5">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={14} className="text-purple-400" />
          <h3 className="font-semibold text-sm">AI Comparative Summary</h3>
          <Badge variant="purple">Multi-hop RAG</Badge>
        </div>
        <p className="text-sm text-muted-foreground text-xs leading-relaxed">
          Use the AI Research Assistant to run multi-ticker comparisons. The assistant will decompose queries, retrieve evidence from SEC filings and news, and synthesize results with source attribution.
        </p>
        <div className="mt-3">
          <Btn variant="primary" size="sm" icon={<MessageSquare size={12} />} onClick={() => navigate("chat")}>Open Chat</Btn>
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 14: Workspaces
// ────────────────────────────────────────────────
function WorkspacesPage({ navigate, firebaseUser }: { navigate: (p: Page) => void; firebaseUser: FirebaseUser | null }) {
  const [showCreate, setShowCreate] = useState(false);
  const [wsName, setWsName] = useState("");
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchWorkspaces = async () => {
      setLoading(true);
      try {
        const res = await apiRequest(`${API_BASE}/workspaces`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setWorkspaces(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    };
    fetchWorkspaces();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">My Workspaces</h1>
          <p className="text-muted-foreground text-sm mt-0.5">Group tickers to track concurrent research themes · Max 50 tickers per workspace</p>
        </div>
        <Btn variant="primary" icon={<Plus size={14} />} onClick={() => setShowCreate(true)}>New Workspace</Btn>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-5"><div className="animate-pulse space-y-3"><div className="h-4 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /><div className="h-3 bg-secondary rounded w-full" /></div></Card>
          ))
        ) : error ? (
          <Card className="p-5 text-sm text-muted-foreground">Unable to load workspaces</Card>
        ) : workspaces.length === 0 ? (
          <div className="text-center py-12 col-span-full text-muted-foreground">
            <Briefcase size={32} className="mx-auto mb-2 opacity-30" />
            <p>No workspaces yet. Create one to get started.</p>
          </div>
        ) : (
        workspaces.map(ws => (
          <Card key={ws.id} className="p-5 cursor-pointer hover:border-primary/30 transition-all" onClick={() => navigate("workspace-detail")}>
            <div className="flex items-start justify-between mb-4">
              <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                <Briefcase size={18} className="text-primary" />
              </div>
              <div className="flex items-center gap-1">
                {ws.alerts > 0 && <Badge variant="hype" className="text-xs">{ws.alerts} alerts</Badge>}
                <button className="p-1 text-muted-foreground hover:text-foreground cursor-pointer" onClick={e => { e.stopPropagation(); navigate("workspace-settings"); }}><MoreVertical size={14} /></button>
              </div>
            </div>
            <h3 className="font-semibold text-foreground mb-1">{ws.name}</h3>
            <p className="text-xs text-muted-foreground mb-4">Created {ws.created_at ? new Date(ws.created_at).toLocaleDateString() : "—"} · {ws.tickers.length} tickers</p>
            <div className="flex flex-wrap gap-1.5">
              {ws.tickers.map(t => (
                <span key={t} className="px-2 py-0.5 bg-secondary rounded-md text-xs font-mono text-muted-foreground border border-border">{t}</span>
              ))}
            </div>
          </Card>
        ))
        )}
        {/* Add card */}
        <button onClick={() => setShowCreate(true)} className="flex flex-col items-center justify-center p-5 rounded-xl border-2 border-dashed border-border hover:border-primary/40 hover:bg-secondary/20 cursor-pointer transition-all min-h-[160px]">
          <Plus size={24} className="text-muted-foreground mb-2" />
          <span className="text-sm text-muted-foreground">Create workspace</span>
        </button>
      </div>

      {showCreate && (
        <Modal title="Create New Workspace" onClose={() => setShowCreate(false)}>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Workspace name</label>
              <Input value={wsName} onChange={setWsName} placeholder="e.g., AI Semiconductor Race" icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Add tickers (optional)</label>
              <Input placeholder="NVDA, AMD, TSLA..." icon={<Hash size={14} />} />
              <p className="text-xs text-muted-foreground">Separate with commas. Max 50 tickers.</p>
            </div>
            <div className="flex gap-2 justify-end pt-2">
              <Btn variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Btn>
              <Btn variant="primary" onClick={() => { setShowCreate(false); navigate("workspace-detail"); }} disabled={!wsName.trim()}>Create Workspace</Btn>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 15: Workspace Detail
// ────────────────────────────────────────────────
function WorkspaceDetailPage({ navigate, setSelectedTicker }: { navigate: (p: Page) => void; setSelectedTicker: (t: string) => void }) {
  const [showAdd, setShowAdd] = useState(false);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspaces")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Workspaces</button>
        <h1 className="text-xl font-bold flex-1">Workspace Detail</h1>
        <Badge variant="neutral">0 / 50 tickers</Badge>
        <Btn variant="secondary" size="sm" icon={<Settings size={12} />} onClick={() => navigate("workspace-settings")}>Settings</Btn>
        <Btn variant="primary" size="sm" icon={<Plus size={12} />} onClick={() => setShowAdd(true)}>Add Ticker</Btn>
      </div>

      {/* Workspace avg scores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Avg Hype Score", value: "—", color: "#F59E0B" },
          { label: "Avg Evidence Score", value: "—", color: "#10B981" },
          { label: "Active Alerts", value: "—", color: "#3B82F6" },
          { label: "Tickers Tracked", value: "0", color: "#8B5CF6" },
        ].map(s => (
          <Card key={s.label} className="p-4">
            <div className="font-mono font-bold text-2xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>

      <Card className="p-6 text-center py-12">
        <Briefcase size={32} className="mx-auto mb-2 opacity-20" />
        <p className="text-muted-foreground text-sm">No tickers in this workspace. Add tickers to start tracking.</p>
      </Card>

      {showAdd && (
        <Modal title="Add Ticker to Workspace" onClose={() => setShowAdd(false)} size="sm">
          <div className="space-y-4">
            <Input placeholder="Search ticker or company name..." icon={<Search size={14} />} />
            <div className="text-center py-6 text-muted-foreground text-xs">
              Tracked tickers will appear here once added.
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 16: Workspace Settings
// ────────────────────────────────────────────────
function WorkspaceSettingsPage({ navigate }: { navigate: (p: Page) => void }) {
  const [name, setName] = useState("AI Semiconductor Race");
  const [showDelete, setShowDelete] = useState(false);
  return (
    <div className="p-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button onClick={() => navigate("workspace-detail")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back</button>
        <h1 className="text-xl font-bold">Workspace Settings</h1>
      </div>
      <div className="space-y-5">
        <Card className="p-5">
          <h3 className="font-semibold mb-4">General</h3>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Workspace name</label>
              <Input value={name} onChange={setName} icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Description (optional)</label>
              <textarea className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none" rows={3} placeholder="Track concurrent AI chip developments..." />
            </div>
            <Btn variant="primary" size="sm" icon={<Check size={12} />}>Save Changes</Btn>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Alert Preferences</h3>
          <div className="space-y-3 text-sm">
            {[
              { label: "Narrative shift alerts", desc: "Notify when Hype/Evidence delta changes ≥10 points", enabled: true },
              { label: "New SEC filings", desc: "Alert on new 10-K, 10-Q, or 8-K filings", enabled: true },
              { label: "Reddit hype spikes", desc: "Alert when post volume increases >200% in 4 hours", enabled: false },
            ].map(a => (
              <div key={a.label} className="flex items-start justify-between gap-4">
                <div>
                  <div className="font-medium text-foreground">{a.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{a.desc}</div>
                </div>
                <div className={cn("relative inline-flex w-10 h-6 rounded-full cursor-pointer transition-colors shrink-0 mt-0.5", a.enabled ? "bg-primary" : "bg-switch-background")}>
                  <div className={cn("absolute top-1 w-4 h-4 rounded-full bg-white transition-transform", a.enabled ? "translate-x-5" : "translate-x-1")} />
                </div>
              </div>
            ))}
          </div>
        </Card>
        <Card className="p-5 border-red-500/20">
          <h3 className="font-semibold mb-2 text-red-400">Danger Zone</h3>
          <p className="text-xs text-muted-foreground mb-4">Soft-deleting archives ticker history but does not permanently remove your research data.</p>
          <Btn variant="secondary" onClick={() => setShowDelete(true)} className="border-red-500/30 text-red-400 hover:bg-red-500/10" icon={<Archive size={12} />}>Archive Workspace</Btn>
        </Card>
      </div>
      {showDelete && (
        <Modal title="Archive Workspace?" onClose={() => setShowDelete(false)} size="sm">
          <p className="text-sm text-muted-foreground mb-4">This will soft-delete the workspace. Your ticker history and research data will be preserved and accessible via the archive for 90 days.</p>
          <div className="flex gap-2 justify-end">
            <Btn variant="secondary" onClick={() => setShowDelete(false)}>Cancel</Btn>
            <Btn variant="danger" onClick={() => navigate("workspaces")} icon={<Archive size={12} />}>Archive</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 17: AI Chat
// ────────────────────────────────────────────────
function ChatPage({ navigate }: { navigate: (p: Page) => void }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; text: string; time: string; sources?: string[] }>>([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const send = () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", text: input, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setTimeout(() => {
      setMessages(m => [...m, { role: "ai", text: "**Analyzing your query...**\n\nI searched across SEC filings, financial news, and community data. Based on available evidence, the claims in your query are partially corroborated. Key SEC disclosures support the revenue figures, but community-driven price projections exceed verifiable guidance by a significant margin.\n\n*Always verify against primary sources before making research decisions.*", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), sources: ["SEC EDGAR", "Alpha Vantage News", "Reddit API"] }]);
      setLoading(false);
    }, 1500);
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <div className="w-9 h-9 rounded-xl bg-purple-500/10 flex items-center justify-center">
          <Sparkles size={18} className="text-purple-400" />
        </div>
        <div>
          <h2 className="font-semibold">AI Research Assistant</h2>
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Radio size={9} className="text-emerald-400 animate-pulse" /> Live · Multi-hop RAG enabled · Sources always cited
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="purple"><Zap size={10} /> Gemini 1.5 Pro</Badge>
          <Btn variant="ghost" size="sm" icon={<Trash2 size={12} />}>Clear</Btn>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* Intro */}
        <div className="flex items-center justify-center">
          <div className="text-xs text-muted-foreground bg-secondary px-3 py-1.5 rounded-full">Today · Session started</div>
        </div>

        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-3", msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
            {msg.role === "ai" ? (
              <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center shrink-0">
                <Sparkles size={14} className="text-purple-400" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shrink-0 text-white text-xs font-bold">IB</div>
            )}
            <div className={cn("max-w-[75%] space-y-2", msg.role === "user" ? "items-end" : "items-start")}>
              <div className={cn("px-4 py-3 rounded-2xl text-sm leading-relaxed", msg.role === "user" ? "bg-primary text-white rounded-tr-sm" : "bg-card border border-border text-foreground rounded-tl-sm")}>
                {msg.text.split("\n").map((line, j) => {
                  const formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>');
                  return <p key={j} className="whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatted || "&nbsp;" }} />;
                })}
              </div>
              {"sources" in msg && msg.sources && (
                <div className="flex flex-wrap gap-1.5 px-1">
                  {(msg.sources as string[]).map(s => <Badge key={s} variant="neutral" className="text-xs">{s}</Badge>)}
                </div>
              )}
              <div className="text-xs text-muted-foreground px-1">{msg.time}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center shrink-0">
              <Sparkles size={14} className="text-purple-400 animate-pulse" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-card border border-border text-sm text-muted-foreground flex items-center gap-2">
              <RefreshCw size={12} className="animate-spin" /> Searching across SEC filings, news, and community data...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Suggested prompts */}
      {messages.length <= 2 && (
        <div className="px-6 pb-3 flex gap-2 flex-wrap">
          {["Compare NVDA vs AMD evidence scores", "What SEC filings support Tesla FSD claims?", "Summarize PLTR earnings narrative"].map(p => (
            <button key={p} className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 cursor-pointer transition-all" onClick={() => setInput(p)}>{p}</button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-6 pb-6">
        <div className="flex gap-2 bg-input-background border border-border rounded-xl p-2 focus-within:border-primary/50 transition-all">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask a complex question about any ticker or topic..."
            rows={2}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none py-1 px-2"
          />
          <button onClick={send} disabled={!input.trim() || loading} className="self-end w-9 h-9 rounded-lg bg-primary text-white flex items-center justify-center hover:bg-primary/90 disabled:opacity-40 cursor-pointer transition-all">
            <Send size={15} />
          </button>
        </div>
        <div className="text-xs text-muted-foreground mt-2 text-center">Not investment advice · AI may make mistakes · Always verify primary sources</div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 18: Alerts
// ────────────────────────────────────────────────
function AlertsPage({ navigate, firebaseUser }: { navigate: (p: Page) => void; firebaseUser: FirebaseUser | null }) {
  const [filter, setFilter] = useState("all");
  const [alerts, setAlerts] = useState<AlertInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const alertTypeIcon = (type: string) => type === "filing" ? <FileText size={14} /> : type === "narrative_shift" ? <Activity size={14} /> : <AlertTriangle size={14} />;
  const alertTypeColor = (t: string) => t === "filing" ? "#10B981" : t === "narrative_shift" ? "#F59E0B" : "#F97316";

  useEffect(() => {
    if (!firebaseUser) return;
    let cancelled = false;
    const fetchAlerts = async () => {
      setLoading(true);
      try {
        const res = await apiRequest(`${API_BASE}/alerts?limit=50`, firebaseUser);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        if (!cancelled) {
          setAlerts(Array.isArray(data) ? data : []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) { setError(true); setLoading(false); }
      }
    };
    fetchAlerts();
    return () => { cancelled = true; };
  }, [firebaseUser]);

  const filtered = filter === "all" ? alerts : filter === "unread" ? alerts.filter(a => !a.read) : alerts.filter(a => a.severity === filter);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Alerts</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{alerts.filter(a => !a.read).length} unread notifications</p>
        </div>
        <Btn variant="secondary" size="sm" icon={<Check size={12} />}>Mark all read</Btn>
      </div>
      <div className="flex gap-2 mb-4 flex-wrap">
        {["all", "unread", "high", "medium", "low"].map(f => (
          <button key={f} onClick={() => setFilter(f)} className={cn("px-3 py-1.5 rounded-lg text-xs border capitalize cursor-pointer transition-all", filter === f ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}>{f}</button>
        ))}
      </div>
      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
          ))
        ) : error ? (
          <Card className="p-4 text-sm text-muted-foreground">Unable to load alerts</Card>
        ) : filtered.length === 0 ? (
          <Card className="p-4 text-sm text-muted-foreground">No alerts match the current filter</Card>
        ) : (
        filtered.map(a => (
          <Card key={a.id} className={cn("p-4 transition-all cursor-pointer hover:border-primary/30", !a.read && "border-primary/20 bg-primary/3")}>
            <div className="flex items-start gap-3">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0" style={{ background: `${alertTypeColor(a.type)}15` }}>
                <span style={{ color: alertTypeColor(a.type) }}>{alertTypeIcon(a.type)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="font-mono font-bold text-sm text-foreground">{a.ticker || "—"}</span>
                  <Badge variant={a.severity === "high" ? "danger" : a.severity === "medium" ? "hype" : "neutral"} className="text-xs">{a.severity}</Badge>
                  <Badge variant="neutral" className="text-xs capitalize">{a.type.replace("_", " ")}</Badge>
                  {!a.read && <span className="w-1.5 h-1.5 rounded-full bg-primary inline-block" />}
                </div>
                <p className="text-sm text-foreground">{a.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{a.time || ""}</p>
              </div>
              <Btn variant="ghost" size="sm" onClick={() => navigate("ticker")} icon={<ArrowRight size={12} />}>View</Btn>
            </div>
          </Card>
        ))
        )}
      </div>

      {/* Subscription settings */}
      <Card className="mt-6 p-5">
        <h3 className="font-semibold mb-4">Alert Subscriptions</h3>
        <p className="text-xs text-muted-foreground mb-3">No tickers are currently subscribed to alerts.</p>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 19: Account Settings (Profile)
// ────────────────────────────────────────────────
function ProfilePage({ navigate, userEmail, userName, userPermissions, loading }: { navigate: (p: Page) => void; userEmail?: string; userName?: string; userPermissions?: string[]; loading?: boolean }) {
  const [activeTab, setActiveTab] = useState("profile");
  const displayName = userName || "";
  const email = userEmail || "";
  const initials = displayName.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "??";
  const [firstName, setFirstName] = useState(displayName.split(" ")[0] || "");
  const [lastName, setLastName] = useState(displayName.split(" ").slice(1).join(" ") || "");
  const [emailVal, setEmailVal] = useState(email || "");
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem("ftd_profile");
      if (raw) {
        const data = JSON.parse(raw);
        if (data.firstName) setFirstName(data.firstName);
        if (data.lastName) setLastName(data.lastName);
        if (data.email) setEmailVal(data.email);
        if (data.photoUrl) setPhotoUrl(data.photoUrl);
      }
    } catch {}
  }, []);

  const handleSaveProfile = () => {
    try {
      localStorage.setItem("ftd_profile", JSON.stringify({ firstName, lastName, email: emailVal, photoUrl }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };
  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Profile</h1>
      <div className="flex gap-2 mb-6 border-b border-border pb-4">
        {["profile", "security", "preferences", "api"].map(t => (
          <button key={t} onClick={() => setActiveTab(t)} className={cn("px-3 py-1.5 rounded-lg text-sm capitalize cursor-pointer transition-all", activeTab === t ? "bg-secondary text-foreground font-medium" : "text-muted-foreground hover:text-foreground")}>{t}</button>
        ))}
      </div>
      {activeTab === "profile" && (
        <div className="space-y-5">
          <Card className="p-5">
            <div className="flex items-center gap-4 mb-5">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white text-xl font-bold overflow-hidden">
                {photoUrl ? <img src={photoUrl} alt="Profile" className="w-full h-full object-cover" /> : initials}
              </div>
              <div>
                <div className="font-semibold text-lg">{displayName || "User"}</div>
                <div className="text-muted-foreground text-sm">{email || "user@example.com"}</div>
                <Badge variant="purple" className="mt-1">Beta User</Badge>
              </div>
              <Btn variant="secondary" size="sm" className="ml-auto" icon={<Edit2 size={12} />} onClick={() => fileInputRef.current?.click()}>Edit Photo</Btn>
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) { const url = URL.createObjectURL(f); setPhotoUrl(url); } }} />
            </div>
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1.5"><label htmlFor="firstName" className="text-sm font-medium">First name</label><Input id="firstName" value={firstName} onChange={setFirstName} placeholder="First name" /></div>
                    <div className="space-y-1.5"><label htmlFor="lastName" className="text-sm font-medium">Last name</label><Input id="lastName" value={lastName} onChange={setLastName} placeholder="Last name" /></div>
                  </div>
                  <div className="space-y-1.5"><label htmlFor="email" className="text-sm font-medium">Email address</label><Input id="email" type="email" value={emailVal} onChange={setEmailVal} placeholder="you@example.com" icon={<Mail size={14} />} /></div>
                  <Btn variant="primary" size="sm" icon={<Check size={12} />} onClick={handleSaveProfile}>{saved ? "Saved" : "Save Profile"}</Btn>
                </div>
            )}
          </Card>
        </div>
      )}
      {activeTab === "security" && (
        <div className="space-y-5">
          <Card className="p-5">
            <h3 className="font-semibold mb-4">Change Password</h3>
            <div className="space-y-3">
              <div className="space-y-1.5"><label className="text-sm font-medium">Current password</label><Input type="password" placeholder="••••••••" icon={<Lock size={14} />} /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">New password</label><Input type="password" placeholder="New password" icon={<Lock size={14} />} /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">Confirm new password</label><Input type="password" placeholder="Confirm password" icon={<Lock size={14} />} /></div>
              <Btn variant="primary" size="sm" icon={<Lock size={12} />}>Update Password</Btn>
            </div>
          </Card>
          <Card className="p-5">
            <h3 className="font-semibold mb-2">Active Sessions</h3>
            <p className="text-xs text-muted-foreground mb-4">Manage devices where you are currently signed in.</p>
            {[{ device: "MacBook Pro · Chrome", location: "San Francisco, CA", time: "Current session", current: true }, { device: "iPhone 15 · Safari", location: "San Francisco, CA", time: "2 days ago", current: false }].map(s => (
              <div key={s.device} className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
                <div>
                  <div className="text-sm font-medium text-foreground">{s.device}</div>
                  <div className="text-xs text-muted-foreground">{s.location} · {s.time}</div>
                </div>
                {s.current ? <Badge variant="evidence">Active</Badge> : <Btn variant="ghost" size="sm" className="text-red-400">Revoke</Btn>}
              </div>
            ))}
          </Card>
        </div>
      )}
      {activeTab === "preferences" && (
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Display Preferences</h3>
          <div className="space-y-4 text-sm">
            {[
              { label: "Compact card view", desc: "Show more tickers per row", enabled: false },
              { label: "Show evidence score by default", desc: "Prioritize evidence over hype display", enabled: true },
              { label: "Email digest (weekly)", desc: "Receive a weekly research summary email", enabled: true },
              { label: "Community posts in feed", desc: "Include Reddit content in main feed", enabled: true },
            ].map(p => (
              <div key={p.label} className="flex items-start justify-between gap-4 py-2 border-b border-border/50 last:border-0">
                <div><div className="font-medium">{p.label}</div><div className="text-xs text-muted-foreground mt-0.5">{p.desc}</div></div>
                <div className={cn("relative inline-flex w-10 h-6 rounded-full cursor-pointer shrink-0 mt-0.5", p.enabled ? "bg-primary" : "bg-switch-background")}>
                  <div className={cn("absolute top-1 w-4 h-4 rounded-full bg-white transition-transform", p.enabled ? "translate-x-5" : "translate-x-1")} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
      {activeTab === "api" && (
        <Card className="p-5">
          <h3 className="font-semibold mb-2">API Access</h3>
          <p className="text-xs text-muted-foreground mb-4">Use the FTD API to programmatically access research data and scores.</p>
          <div className="p-3 bg-secondary/50 rounded-lg border border-border font-mono text-xs text-muted-foreground mb-3 flex items-center justify-between">
            <span>ftd_beta_••••••••••••••••••••</span>
            <button className="text-primary hover:underline cursor-pointer flex items-center gap-1"><Copy size={10} /> Copy</button>
          </div>
          <div className="flex gap-2">
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Regenerate Key</Btn>
            <Btn variant="ghost" size="sm" icon={<ExternalLink size={12} />}>API Docs</Btn>
          </div>
        </Card>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 20: Admin Dashboard
// ────────────────────────────────────────────────
function AdminDashboard({ navigate, firebaseUser }: { navigate: (p: Page) => void; firebaseUser: FirebaseUser | null }) {
  const accuracy = 76;
  const [kpiData, setKpiData] = useState<{ label: string; value: string; sub: string; color: string; icon: any } | null>(null);
  const [pipelineData, setPipelineData] = useState<any[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        const res = await apiRequest(`${API_BASE}/dashboard/stats`, null);
        if (!res.ok) throw new Error("failed");
        const data = await res.json();
        setKpiData({
          label: "Articles Ingested",
          value: data.articles_count?.toLocaleString() || "-",
          sub: "Total in system",
          color: "#3B82F6",
          icon: Database,
        });
        setPipelineData(null);
      } catch {
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchAdminData();
  }, []);

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Admin Operations Portal</h1>
            <p className="text-muted-foreground text-sm mt-0.5">System KPIs · Data pipeline status · Mapping accuracy</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="neutral"><Radio size={9} className="text-emerald-400" /> Loading...</Badge>
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Refresh</Btn>
          </div>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="p-4"><div className="animate-pulse space-y-2"><div className="h-3 bg-secondary rounded w-3/4" /><div className="h-3 bg-secondary rounded w-1/2" /></div></Card>
          ))}
        </div>
      </div>
    );
  }
  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Admin Operations Portal</h1>
            <p className="text-muted-foreground text-sm mt-0.5">System KPIs · Data pipeline status · Mapping accuracy</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="neutral"><Radio size={9} className="text-emerald-400" /> All systems operational</Badge>
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Refresh</Btn>
          </div>
        </div>
        <Card className="p-6 text-center">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to load admin dashboard data</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Admin Operations Portal</h1>
          <p className="text-muted-foreground text-sm mt-0.5">System KPIs · Data pipeline status · Mapping accuracy</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="neutral"><Radio size={9} className="text-emerald-400" /> All systems operational</Badge>
          <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Refresh</Btn>
        </div>
      </div>

      {/* High-priority alert */}
      {accuracy < 80 && (
        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/30 rounded-xl mb-6">
          <AlertCircle size={18} className="text-red-400 shrink-0" />
          <div className="flex-1">
            <div className="font-semibold text-sm text-red-400">Mapping Accuracy Below Threshold</div>
            <div className="text-xs text-red-400/80">Auto-mapping success rate is {accuracy}% — below the 80% operational minimum. Review queue requires immediate attention.</div>
          </div>
          <Btn variant="danger" size="sm" onClick={() => navigate("admin-mapping")}>Review Queue</Btn>
        </div>
      )}

      {/* KPI grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs text-muted-foreground mb-1">Articles Ingested</div>
              <div className="font-mono font-bold text-2xl text-foreground">{kpiData?.value ?? "—"}</div>
              <div className="text-xs text-muted-foreground mt-0.5">{kpiData?.sub ?? ""}</div>
            </div>
            <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${kpiData?.color ?? "#3B82F6"}15` }}>
              {kpiData?.icon ? <kpiData.icon size={18} style={{ color: kpiData.color }} /> : <Database size={18} className="text-muted-foreground" />}
            </div>
          </div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Mapped Tickers</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground mt-0.5">No live data</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Queue Pending Review</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">0</div>
          <div className="text-xs text-muted-foreground mt-0.5">Queue is clear</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Active Users (7d)</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground mt-0.5">No live data</div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline status */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold">Pipeline Status</h2>
            <button onClick={() => navigate("admin-system")} className="text-xs text-primary hover:underline cursor-pointer">System details →</button>
          </div>
          <Card>
            <div className="p-4 text-center text-muted-foreground">
              <Database size={24} className="mx-auto mb-2 opacity-30" />
              <p>No pipeline data available</p>
            </div>
          </Card>
        </div>

        {/* Quick links */}
        <div className="space-y-4">
          <h2 className="font-semibold">Admin Actions</h2>
          <div className="space-y-2">
            {[
              { label: "Mapping Review Queue", desc: "Review mapping issues", icon: AlertTriangle, page: "admin-mapping" as Page, urgent: true },
              { label: "User Management", desc: "Manage applications users", icon: Users, page: "admin-users" as Page, urgent: false },
              { label: "System Monitor", desc: "View pipeline details", icon: Activity, page: "admin-system" as Page, urgent: false },
            ].map(a => (
              <Card key={a.label} className={cn("p-4 cursor-pointer hover:border-primary/30 transition-all", a.urgent && "border-red-500/20")} onClick={() => navigate(a.page)}>
                <div className="flex items-center gap-3">
                  <a.icon size={16} className={a.urgent ? "text-red-400" : "text-muted-foreground"} />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{a.label}</div>
                    <div className="text-xs text-muted-foreground">{a.desc}</div>
                  </div>
                  <ChevronRight size={14} className="text-muted-foreground" />
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 21: Admin Mapping Queue
// ────────────────────────────────────────────────
function AdminMappingPage({ navigate }: { navigate: (p: Page) => void }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [actionModal, setActionModal] = useState<{ id: string; action: string } | null>(null);

  const resolve = (id: string, action: string) => {
    setItems(prev => prev.filter(i => i.id !== id));
    setActionModal(null);
    setSelected(null);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("admin")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Admin</button>
        <h1 className="text-xl font-bold flex-1">Mapping Review Queue</h1>
        <Badge variant="danger">{items.length} pending</Badge>
        <Btn variant="secondary" size="sm" icon={<Filter size={12} />}>Filter</Btn>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Queue list */}
        <div className="lg:col-span-3 space-y-2">
          {items.map(item => (
            <Card key={item.id} className={cn("p-4 cursor-pointer transition-all hover:border-primary/20", selected === item.id && "border-primary/50 bg-primary/5")} onClick={() => setSelected(item.id)}>
              <div className="flex items-start gap-3">
                <div className={cn("px-1.5 py-0.5 rounded text-xs font-mono font-bold shrink-0", item.reporter === "user" ? "bg-orange-500/15 text-orange-400" : "bg-blue-500/15 text-blue-400")}>
                  {item.reporter === "user" ? "USR" : "AUTO"}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-foreground leading-snug mb-1 truncate">{item.article}</div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{item.source}</span>
                    <span>·</span>
                    <span>Mapped: <strong className="text-foreground">{item.mapped}</strong></span>
                    <span>→ Suggested: <strong className="text-primary">{item.suggested}</strong></span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={item.confidence < 0.5 ? "danger" : item.confidence < 0.7 ? "hype" : "evidence"} className="text-xs">
                      {Math.round(item.confidence * 100)}% confidence
                    </Badge>
                    <Badge variant="neutral" className="text-xs">{item.type}</Badge>
                    <span className="text-xs text-muted-foreground">{item.time}</span>
                  </div>
                </div>
              </div>
            </Card>
          ))}
          {items.length === 0 && (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              <div className="text-center">
                <CheckCircle size={24} className="mx-auto mb-2 text-emerald-400" />
                Queue is clear
              </div>
            </div>
          )}
        </div>

        {/* Review panel */}
        <div className="lg:col-span-2">
          {selected ? (() => {
            const item = items.find(i => i.id === selected)!;
            if (!item) return null;
            return (
              <Card className="p-5 sticky top-0">
                <h3 className="font-semibold mb-4">Review Record</h3>
                <div className="space-y-3 text-sm">
                  <div className="p-3 bg-secondary/50 rounded-lg">
                    <div className="text-xs text-muted-foreground mb-1">Article</div>
                    <div className="font-medium text-foreground text-sm leading-snug">{item.article}</div>
                    <div className="text-xs text-muted-foreground mt-1">{item.source}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-secondary/30 rounded-lg text-center">
                      <div className="text-xs text-muted-foreground">Current Mapping</div>
                      <div className="font-mono font-bold text-lg text-foreground">{item.mapped}</div>
                    </div>
                    <div className="p-3 bg-primary/10 rounded-lg text-center">
                      <div className="text-xs text-muted-foreground">Suggested Fix</div>
                      <div className="font-mono font-bold text-lg text-primary">{item.suggested}</div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Confidence</span>
                    <span className="font-mono font-semibold" style={{ color: item.confidence >= 0.7 ? "#10B981" : item.confidence >= 0.5 ? "#F59E0B" : "#EF4444" }}>{Math.round(item.confidence * 100)}%</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">Reported by</span>
                    <Badge variant={item.reporter === "user" ? "hype" : "default"} className="text-xs">{item.reporter === "user" ? "User report" : "Auto-flagged"}</Badge>
                  </div>
                </div>
                <div className="mt-5 space-y-2">
                  <Btn variant="primary" className="w-full justify-center" icon={<Check size={13} />} onClick={() => { resolve(item.id, "approve"); }}>Approve & Remap to {item.suggested}</Btn>
                  <Btn variant="secondary" className="w-full justify-center" icon={<Archive size={13} />} onClick={() => resolve(item.id, "dismiss")}>Dismiss Report</Btn>
                  <Btn variant="secondary" className="w-full justify-center" icon={<RefreshCw size={13} />} onClick={() => resolve(item.id, "reroute")}>Re-route to Fuzzy Search</Btn>
                </div>
              </Card>
            );
          })() : (
            <div className="flex items-center justify-center h-48 text-muted-foreground text-sm">
              <div className="text-center">
                <AlertTriangle size={24} className="mx-auto mb-2 opacity-30" />
                <p>Select a record to review</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 22: Admin Users
// ────────────────────────────────────────────────
function AdminUsersPage({ navigate }: { navigate: (p: Page) => void }) {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("admin")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Admin</button>
        <h1 className="text-xl font-bold flex-1">User Management</h1>
        <Badge variant="neutral">{users.length} users</Badge>
      </div>
      <div className="flex items-center gap-3 mb-4">
        <Input placeholder="Search users..." icon={<Search size={14} />} className="max-w-sm" />
        <Btn variant="secondary" size="sm" icon={<Filter size={12} />}>Filter</Btn>
      </div>
      <Card>
        <div className="divide-y divide-border">
          <div className="grid grid-cols-[1fr_1fr_80px_100px_80px_80px_80px] gap-4 px-4 py-2 text-xs text-muted-foreground font-medium uppercase tracking-wide">
            <span>User</span><span>Email</span><span>Role</span><span>Joined</span><span>Searches</span><span>WS</span><span>Status</span>
          </div>
          {users.length === 0 && (
            <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
              <div className="text-center">
                <Users size={24} className="mx-auto mb-2 opacity-30" />
                <p>No users found</p>
              </div>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 23: Admin System Monitor
// ────────────────────────────────────────────────
function AdminSystemPage({ navigate }: { navigate: (p: Page) => void }) {
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("admin")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Admin</button>
        <h1 className="text-xl font-bold flex-1">System Monitor</h1>
        <Badge variant="neutral"><Radio size={9} className="text-emerald-400" /> No live data</Badge>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">CPU Usage</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">No monitoring data available</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Memory</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">No monitoring data available</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Vector DB Queries/s</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">No monitoring data available</div>
        </Card>
        <Card className="p-4 text-center">
          <div className="text-xs text-muted-foreground mb-1">Cache Hit Rate</div>
          <div className="font-mono font-bold text-2xl text-muted-foreground">—</div>
          <div className="text-xs text-muted-foreground">No monitoring data available</div>
        </Card>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Pipeline Health</h3>
          <div className="text-center py-8 text-muted-foreground">
            <Database size={24} className="mx-auto mb-2 opacity-30" />
            <p>No pipeline health data available</p>
          </div>
        </Card>
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Ingestion Volume (24h)</h3>
          <div className="text-center py-8 text-muted-foreground">
            <Database size={24} className="mx-auto mb-2 opacity-30" />
            <p>No ingestion data available</p>
          </div>
        </Card>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// MODAL: Error Report
// ────────────────────────────────────────────────
function ReportModal({ onClose }: { onClose: () => void }) {
  const [reason, setReason] = useState("wrong-ticker");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <Modal title="Report Submitted" onClose={onClose} size="sm">
        <div className="text-center space-y-4 py-4">
          <div className="w-14 h-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto">
            <CheckCircle size={28} className="text-emerald-400" />
          </div>
          <div>
            <h3 className="font-semibold mb-1">Feedback received</h3>
            <p className="text-sm text-muted-foreground">Your report has been added to the admin review queue. No changes were made to the live view for other users.</p>
          </div>
          <Badge variant="neutral"><Info size={10} /> Queue position #18 · Est. review: 4 hours</Badge>
          <Btn variant="primary" className="w-full justify-center" onClick={onClose}>Close</Btn>
        </div>
      </Modal>
    );
  }

  return (
    <Modal title="Report Mapping Error" onClose={onClose}>
      <div className="space-y-4">
        <div className="p-3 bg-secondary/50 rounded-lg border border-border text-xs text-muted-foreground">
          Use this form to report mapping issues for any article.
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Reason for report</label>
          <select value={reason} onChange={e => setReason(e.target.value)} className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary/50">
            <option value="wrong-ticker">Wrong ticker mapping</option>
            <option value="wrong-source">Incorrect source attribution</option>
            <option value="false-claim">False or misleading claim extracted</option>
            <option value="duplicate">Duplicate article</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium">Additional context (optional)</label>
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            rows={3}
            placeholder="Describe the issue in more detail..."
            className="w-full bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 resize-none"
          />
        </div>
        <p className="text-xs text-muted-foreground">Submitting will add this to the admin review queue. The article will remain visible to all users until a review decision is made.</p>
        <div className="flex gap-2 justify-end">
          <Btn variant="secondary" onClick={onClose}>Cancel</Btn>
          <Btn variant="primary" onClick={() => setSubmitted(true)} icon={<Send size={12} />}>Send Report</Btn>
        </div>
      </div>
    </Modal>
  );
}

// ────────────────────────────────────────────────
// Main App
// ────────────────────────────────────────────────
export default function App() {
  const [page, setPage] = useState<Page>("login");
  const [selectedTicker, setSelectedTicker] = useState("NVDA");
  const [showReport, setShowReport] = useState(false);
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [userPermissions, setUserPermissions] = useState<string[]>([]);
  const [profileLoading, setProfileLoading] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(firebaseAuth, async (user) => {
      setFirebaseUser(user);
      if (user) {
        setProfileLoading(true);
        try {
          const [profileRes, permsRes] = await Promise.all([
            apiRequest("/auth/me/user", user),
            apiRequest("/users/me/permissions", user),
          ]);
          if (profileRes.ok) {
            const profile = await profileRes.json();
            setUserProfile(profile);
          }
          if (permsRes.ok) {
            const perms = await permsRes.json();
            setUserPermissions(perms.permissions || []);
          }
        } catch {
          // ignore fetch errors during initial auth state resolution
        } finally {
          setProfileLoading(false);
        }
      } else {
        setUserProfile(null);
        setUserPermissions([]);
      }
    });
    return () => unsubscribe();
  }, []);

  const navigate = (p: Page) => setPage(p);

  const handleSignOut = async () => {
    try { await signOut(firebaseAuth); } catch {}
    navigate("login");
  };

  const publicPages: Page[] = ["login", "register", "verify-email", "forgot-password", "onboarding-done"];
  const isPublic = publicPages.includes(page);

  const userEmail = firebaseUser?.email || userProfile?.email || "";
  const userName = firebaseUser?.displayName || userProfile?.email?.split("@")[0] || "";

  const renderPage = () => {
    switch (page) {
      case "login": return <LoginPage navigate={navigate} />;
      case "register": return <RegisterPage navigate={navigate} />;
      case "verify-email": return <VerifyEmailPage navigate={navigate} userEmail={firebaseUser?.email} />;
      case "forgot-password": return <ForgotPasswordPage navigate={navigate} />;
      case "onboarding-done": return <OnboardingPage navigate={navigate} />;
      case "dashboard": return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
      case "search": return <SearchPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
      case "ticker": return <TickerDashboard navigate={navigate} ticker={selectedTicker} onReport={() => setShowReport(true)} firebaseUser={firebaseUser} />;
      case "ticker-timeline": return <TimelinePage navigate={navigate} ticker={selectedTicker} firebaseUser={firebaseUser} />;
      case "tickers-filings": return <FilingsPage navigate={navigate} ticker={selectedTicker} firebaseUser={firebaseUser} />;
      case "ticker-community": return <CommunityPage navigate={navigate} ticker={selectedTicker} />;
      case "ticker-comparison": return <ComparisonPage navigate={navigate} firebaseUser={firebaseUser} />;
      case "workspaces": return <WorkspacesPage navigate={navigate} firebaseUser={firebaseUser} />;
      case "workspace-detail": return <WorkspaceDetailPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
      case "workspace-settings": return <WorkspaceSettingsPage navigate={navigate} />;
      case "chat": return <ChatPage navigate={navigate} />;
      case "alerts": return <AlertsPage navigate={navigate} firebaseUser={firebaseUser} />;
      case "profile": return <ProfilePage navigate={navigate} userEmail={userEmail} userName={userName} userPermissions={userPermissions} loading={profileLoading} />;
      case "admin": return <AdminDashboard navigate={navigate} firebaseUser={firebaseUser} />;
      case "admin-mapping": return <AdminMappingPage navigate={navigate} />;
      case "admin-users": return <AdminUsersPage navigate={navigate} />;
      case "admin-system": return <AdminSystemPage navigate={navigate} />;
      default: return <DashboardPage navigate={navigate} setSelectedTicker={setSelectedTicker} firebaseUser={firebaseUser} />;
    }
  };

  return (
    <>
      {isPublic ? (
        <div className="min-h-screen bg-background">{renderPage()}</div>
      ) : (
        <AppShell page={page} navigate={navigate} userEmail={userEmail} userName={userName} onSignOut={handleSignOut}>
          {renderPage()}
        </AppShell>
      )}
      {showReport && <ReportModal onClose={() => setShowReport(false)} />}
    </>
  );
}

// ────────────────────────────────────────────────
// Preserved Components
// ────────────────────────────────────────────────

function LegacyLandingPage({ navigate }: { navigate: (p: Page) => void }) {
  return (
    <div className="min-h-screen bg-background overflow-hidden">
      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
            <BarChart size={16} className="text-white" />
          </div>
          <span className="font-bold text-xl text-foreground tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          <Badge variant="purple" className="ml-1">Beta</Badge>
        </div>
        <div className="flex items-center gap-3">
          <Btn variant="ghost" onClick={() => navigate("login")}>Sign In</Btn>
          <Btn variant="primary" onClick={() => navigate("register")}>Get Started Free</Btn>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative px-8 pt-24 pb-20 text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent pointer-events-none" />
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/5 rounded-full blur-3xl pointer-events-none" />
        <Badge variant="purple" className="mb-4 text-sm px-3 py-1">
          <Sparkles size={12} /> AI-Powered Research
        </Badge>
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 max-w-4xl mx-auto" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Separate{" "}
          <span style={{ color: "#F59E0B" }}>Hype</span>
          {" "}from{" "}
          <span style={{ color: "#10B981" }}>Evidence</span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-2xl mx-auto mb-10 leading-relaxed">
          FTD aggregates financial news, SEC filings, and community discussions — then uses AI to score every claim on an evidence scale. Stop guessing. Start researching.
        </p>
        <div className="flex items-center justify-center gap-3 flex-wrap">
          <Btn variant="primary" size="lg" onClick={() => navigate("register")} icon={<ArrowRight size={16} />}>
            Start Researching
          </Btn>
          <Btn variant="outline" size="lg" onClick={() => navigate("login")}>
            View Demo
          </Btn>
        </div>
      </section>

      {/* Demo Preview Card */}
      <section className="px-8 pb-16 max-w-5xl mx-auto">
        <div className="relative rounded-2xl border border-border/50 overflow-hidden bg-card/50 backdrop-blur shadow-2xl shadow-black/30">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-border/50 bg-card/80">
            <div className="flex gap-1.5"><div className="w-2.5 h-2.5 rounded-full bg-red-500/70" /><div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" /><div className="w-2.5 h-2.5 rounded-full bg-green-500/70" /></div>
            <span className="text-xs text-muted-foreground mx-auto">ftd.research — NVDA Dashboard</span>
          </div>
          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-xl text-foreground">NVDA</span>
                    <Badge variant="neutral">NASDAQ</Badge>
                  </div>
                  <div className="text-muted-foreground text-sm mt-0.5">NVIDIA Corporation</div>
                </div>
                <div className="text-right">
                  <div className="font-mono font-bold text-lg text-foreground">$873.50</div>
                  <div className="text-emerald-400 text-sm flex items-center gap-1 justify-end"><TrendingUp size={12} />+4.2%</div>
                </div>
              </div>
              <HypeEvidenceBar hype={84} evidence={71} />
              {NEWS_ARTICLES.slice(0, 2).map(a => (
                <div key={a.id} className="flex items-start gap-3 p-3 bg-secondary/50 rounded-lg border border-border/50">
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-muted-foreground mb-1">{a.source} · {a.time}</div>
                    <div className="text-sm font-medium text-foreground truncate">{a.headline}</div>
                  </div>
                  <div className="flex flex-col items-end gap-1 shrink-0">
                    <span className="text-xs font-mono" style={{ color: getHypeColor(a.hype) }}>H:{a.hype}</span>
                    <span className="text-xs font-mono" style={{ color: getEvidenceColor(a.evidence) }}>E:{a.evidence}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="space-y-3">
              <div className="p-3 bg-secondary/50 rounded-lg border border-border/50">
                <div className="text-xs text-muted-foreground mb-2">Hype vs Evidence</div>
                <div className="text-3xl font-mono font-bold" style={{ color: "#F59E0B" }}>84</div>
                <div className="text-xs text-muted-foreground">vs. Evidence <span style={{ color: "#10B981" }}>71</span></div>
              </div>
              <div className="p-3 bg-secondary/50 rounded-lg border border-border/50">
                <div className="text-xs text-muted-foreground mb-2">AI Summary</div>
                <div className="text-xs text-foreground leading-relaxed">Blackwell GPU production claims are partially corroborated by TSMC supply chain data, but $2000 PT targets lack quantitative support.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="px-8 pb-20 max-w-5xl mx-auto">
        <h2 className="text-3xl font-bold text-center mb-12" style={{ fontFamily: "'Outfit', sans-serif" }}>Everything a serious researcher needs</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { icon: BarChart2, title: "Hype vs. Evidence Scoring", desc: "Every article and claim scored on a 0–100 evidence scale, aggregated from news, filings, and community.", color: "#F59E0B" },
            { icon: FileText, title: "SEC Filing Integration", desc: "Automatically parsed 10-K, 10-Q, and 8-K filings with XBRL data extraction and section mapping.", color: "#10B981" },
            { icon: MessageSquare, title: "AI Multi-Hop Queries", desc: "Ask complex comparative questions across multiple tickers. The AI decomposes, retrieves, and synthesizes with source attribution.", color: "#8B5CF6" },
            { icon: Clock, title: "Narrative Timelines", desc: "Chronological view of how a thesis evolved over time — from early Reddit speculation to confirmed SEC disclosures.", color: "#0EA5E9" },
            { icon: Briefcase, title: "Research Workspaces", desc: "Group up to 50 tickers into themed research workspaces. Track them all together with workspace-level scoring.", color: "#3B82F6" },
            { icon: AlertTriangle, title: "Narrative Shift Alerts", desc: "Get notified when Hype vs. Evidence deltas exceed 10 points — catch narrative reversals before the crowd.", color: "#EF4444" },
          ].map(f => (
            <Card key={f.title} className="p-5">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: `${f.color}15` }}>
                <f.icon size={20} style={{ color: f.color }} />
              </div>
              <h3 className="font-semibold text-foreground mb-2 text-sm">{f.title}</h3>
              <p className="text-muted-foreground text-sm leading-relaxed">{f.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-8 pb-20 text-center">
        <div className="max-w-xl mx-auto p-10 bg-gradient-to-br from-primary/10 to-accent/5 rounded-2xl border border-primary/20">
          <h2 className="text-3xl font-bold mb-3" style={{ fontFamily: "'Outfit', sans-serif" }}>Start your research today</h2>
          <p className="text-muted-foreground mb-6 text-sm">Free access during beta. No credit card required.</p>
          <Btn variant="primary" size="lg" onClick={() => navigate("register")}>Create Free Account</Btn>
        </div>
      </section>
    </div>
  );
}
