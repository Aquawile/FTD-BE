// ────────────────────────────────────────────────
// PROFILE PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Badge, Button as Btn, ChevronLeft, User, Settings, LogOut, Bell, Shield, Key, Mail, ExternalLink, CheckCircle } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface ProfilePageProps {
  navigate: (p: string) => void;
}

export function ProfilePage({ navigate }: ProfilePageProps) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${localStorage.getItem("auth_token")}` }
    })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(data => { if (!cancelled) { setUser(data); setLoading(false); } })
      .catch(() => { if (!cancelled) { setError(true); setLoading(false); } })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { /* cancelled = true */ };
  }, []);

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="text-center py-12 text-muted-foreground">
          <AlertCircle size={32} className="mx-auto mb-2 opacity-50" />
          <p>Unable to load profile</p>
        </div>
      )}

      {!loading && !error && user && (
        <div>
          <div className="mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">{user.name || user.email}</h1>
                <p className="text-muted-foreground text-sm mt-1">{user.email}</p>
              </div>
              <div className="flex gap-2">
                <Btn variant="secondary" size="sm" icon={<Settings size={12} />}>Settings</Btn>
                <Btn variant="secondary" size="sm" icon={<LogOut size={12} />} onClick={() => { localStorage.removeItem("auth_token"); navigate("login"); }}>Logout</Btn>
              </div>
            </div>

            <div className="flex gap-4 mb-6 border-b border-border">
              {["overview", "security", "notifications", "integrations"].map(tab => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn("px-4 py-2 text-sm font-medium border-b-2 transition-all", activeTab === tab ? "border-primary text-primary" : "border-transparent text-muted-foreground hover:text-foreground")}
                >
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {activeTab === "overview" && (
              <div className="space-y-6">
                <Card className="p-5">
                  <h3 className="font-semibold mb-4">Account Information</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Email</label>
                      <p className="font-mono text-sm">{user.email}</p>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">User ID</label>
                      <p className="font-mono text-sm">{user.id}</p>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Role</label>
                      <Badge variant="default">{user.role || "user"}</Badge>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Joined</label>
                      <p className="text-sm">{user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}</p>
                    </div>
                  </div>
                </Card>

                <Card className="p-5">
                  <h3 className="font-semibold mb-4">Permissions</h3>
                  <div className="space-y-2">
                    {["tickers.search", "tickers.news", "tickers.prices", "tickers.filings", "tickers.timeline", "tickers.insights", "dashboard.read", "alerts.read", "alerts.write", "workspaces.read", "workspaces.write", "admin.access"].map(p => (
                      <div key={p} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                        <span className="text-xs font-mono text-muted-foreground">{p}</span>
                        <Badge variant="evidence">Granted</Badge>
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            </div>

            {activeTab === "security" && (
              <div className="space-y-6">
                <Card className="p-5">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><Key size={16} /> Security</h3>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between p-4 bg-secondary/30 rounded-lg">
                      <div>
                        <p className="font-medium">Two-Factor Authentication</p>
                        <p className="text-xs text-muted-foreground">Add an extra layer of security to your account</p>
                      </div>
                      <Btn variant="secondary" size="sm">Enable 2FA</Btn>
                    </div>
                    <div className="flex items-center justify-between p-4 border-t border-border/50">
                      <div>
                        <p className="font-medium">Password</p>
                        <p className="text-xs text-muted-foreground">Last changed 30 days ago</p>
                      </div>
                      <Btn variant="secondary" size="sm">Change Password</Btn>
                    </div>
                    <div className="flex items-center justify-between p-4">
                      <div>
                        <p className="font-medium">Active Sessions</p>
                        <p className="text-xs text-muted-foreground">2 active sessions</p>
                      </div>
                      <Btn variant="secondary" size="sm">Manage Sessions</Btn>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {activeTab === "notifications" && (
              <div className="space-y-4">
                <Card className="p-5">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><Bell size={16} /> Notifications</h3>
                  <div className="space-y-3">
                    {["New alert for tracked ticker", "Weekly digest", "Price alerts", "Filing notifications", "Community mentions"].map((n, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                        <span className="text-sm">{n}</label>
                        <span className="relative inline-flex"><input type="checkbox" className="w-4 h-4 rounded border-border text-primary focus:ring-primary" defaultChecked /></span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            )}

            {activeTab === "integrations" && (
              <div className="space-y-4">
                <Card className="p-5">
                  <h3 className="font-semibold mb-4 flex items-center gap-2"><ExternalLink size={16} /> Integrations</h3>
                  <div className="space-y-3">
                    {["Google", "Slack", "Discord", "Notion", "Telegram"].map(s => (
                      <div key={s} className="flex items-center justify-between p-3 bg-secondary/30 rounded-lg border border-border/50">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                            <ExternalLink size={14} className="text-muted-foreground" />
                          </div>
                          <span className="font-medium">{s}</span>
                        </div>
                        <Btn variant="secondary" size="sm">Connect</Btn>
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfilePage;