// ────────────────────────────────────────────────
// ADMIN PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, Users, Database, Settings, AlertTriangle, Shield, Search, Filter, MoreHorizontal, Edit2, Trash2, Plus, Download, Eye, RefreshCw } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface AdminPageProps {
  navigate: (p: string) => void;
}

export function AdminPage({ navigate }: AdminPageProps) {
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [search, setSearch] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/admin/users")
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setUsers(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  const tabs = [
    { id: "users", label: "Users", icon: Users },
    { id: "permissions", label: "Permissions", icon: Shield },
    { id: "data", label: "Data Quality", icon: Database },
    { id: "system", label: "System Health", icon: AlertTriangle },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Admin Panel</h1>
          <p className="text-muted-foreground text-sm mt-1">System administration and monitoring</p>
        </div>
        <Btn variant="primary" icon={<Plus size={14} /}>Add User</Btn>
      </div>

      <div className="flex gap-2 mb-6 border-b border-border">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-all`,
              tab === t.id ? "border-primary text-primary" : tab === "permissions" ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground"
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-muted-foreground">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to load admin data</p>
        </div>
      )}

      {!loading && !error && (
        <div>
          {tab === "users" && (
            <div className="space-y-4">
              <div className="flex gap-2 mb-4">
                <div className="relative flex-1 max-w-md">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <input
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search users..."
                    className="w-full pl-9 pr-3 py-2 bg-input-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
                  />
                </div>
                <Btn variant="primary" icon={<Plus size={12} /}>Add User</Btn>
              </div>

              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="text-xs text-muted-foreground border-b border-border">
                        <th className="px-4 py-3 text-left">User</th>
                        <th className="px-4 py-3 text-left">Email</th>
                        <th className="px-4 py-3 text-left">Role</th>
                        <th className="px-4 py-3 text-left">Permissions</th>
                        <th className="px-4 py-3 text-left">Status</th>
                        <th className="px-4 py-3 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { id: 1, name: "John Smith", email: "john@company.com", role: "Admin", permissions: ["admin.access", "tickers.search", "alerts.write"], status: "Active" },
                        { id: 2, name: "Sarah Chen", email: "sarah@company.com", role: "Analyst", permissions: ["tickers.search", "alerts.read"], status: "Active" },
                        { id: 3, name: "Mike Johnson", email: "mike@company.com", role: "Viewer", permissions: ["tickers.search"], status: "Active" },
                        { id: 4, name: "Emily Davis", email: "emily@company.com", role: "Analyst", permissions: ["tickers.search", "tickers.news", "alerts.read"], status: "Pending" },
                      ].map(u => (
                        <tr key={u.id} className="border-b border-border/50 hover:bg-secondary/30">
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-3">
                              <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                                <span className="font-mono font-bold text-xs text-foreground">{u.name.slice(0, 2).toUpperCase()}</span>
                              </div>
                              <div>
                                <div className="font-medium text-sm text-foreground">{u.name}</div>
                                <div className="text-xs text-muted-foreground">{u.email}</div>
                              </div>
                            </td>
                            <td className="px-4 py-4"><Badge variant={u.role === "Admin" ? "danger" : u.role === "Analyst" ? "hype" : "neutral"} className="text-xs">{u.role}</Badge></td>
                            <td className="px-4 py-4">
                              <div className="flex flex-wrap gap-1">
                                {u.permissions.map((p: string) => (
                                  <Badge key={p} variant="neutral" className="text-xs">{p}</Badge>
                                ))}
                              </td>
                            <td className="px-4 py-4"><Badge variant={u.status === "Active" ? "evidence" : u.status === "Pending" ? "hype" : "neutral"} className="text-xs">{u.status}</Badge></td>
                            <td className="px-4 py-4 text-right">
                              <div className="flex items-center gap-1">
                                <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors cursor-pointer" title="View"><Eye size={12} /></button>
                                <button className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-secondary rounded-lg transition-colors cursor-pointer" title="Edit"><Edit2 size={12} /></button>
                                <button className="p-1.5 text-muted-foreground hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors cursor-pointer" title="Delete"><Trash2 size={12} /></button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminPage;