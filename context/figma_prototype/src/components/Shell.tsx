import { useState, useRef, useEffect } from "react";
import { Page } from "../app/types";
import { cn } from "./ui";
import {
  Home, Search, Briefcase, Clock, MessageSquare, Bell, Shield,
  BarChart, ChevronRight, ChevronLeft, Settings,
} from "lucide-react";

// ────────────────────────────────────────────────
// Layout Shell
// ────────────────────────────────────────────────
export function Sidebar({ page, navigate, collapsed, onCollapse, unreadAlerts = 0 }: {
  page: Page; navigate: (p: Page) => void; collapsed: boolean; onCollapse: () => void; unreadAlerts?: number;
}) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: Home },
    { id: "search", label: "Research", icon: Search },
    { id: "workspaces", label: "Workspaces", icon: Briefcase },
    { id: "alerts", label: "Alerts", icon: Bell },
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
              <span className="relative shrink-0">
                <Icon size={16} />
                {collapsed && item.id === "alerts" && unreadAlerts > 0 && <span className="absolute -top-1 -right-1 w-2 h-2 bg-orange-500 rounded-full" />}
              </span>
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.id === "alerts" && unreadAlerts > 0 && (
                <span className="ml-auto min-w-5 h-5 px-1.5 rounded-full bg-orange-500 text-white text-[10px] font-semibold flex items-center justify-center">
                  {unreadAlerts > 99 ? "99+" : unreadAlerts}
                </span>
              )}
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

export function TopBar({ navigate, searchQuery, setSearchQuery, onSearch, unreadAlerts = 0, userEmail, userName, onSignOut }: {
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
          {unreadAlerts > 0 && <span className="absolute top-1 right-1 w-2 h-2 bg-orange-500 rounded-full" aria-label={`${unreadAlerts} unread alerts`} />}
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

export function AppShell({ page, navigate, children, userEmail, userName, onSignOut, unreadAlerts = 0 }: { page: Page; navigate: (p: Page) => void; children: React.ReactNode; userEmail?: string; userName?: string; onSignOut?: () => void; unreadAlerts?: number }) {
  const [collapsed, setCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const handleSearch = () => { if (searchQuery.trim()) navigate("search"); };
  return (
    <div className="flex min-h-screen">
      <Sidebar page={page} navigate={navigate} collapsed={collapsed} onCollapse={() => setCollapsed(c => !c)} unreadAlerts={unreadAlerts} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar navigate={navigate} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onSearch={handleSearch} unreadAlerts={unreadAlerts} userEmail={userEmail} userName={userName} onSignOut={onSignOut} />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

