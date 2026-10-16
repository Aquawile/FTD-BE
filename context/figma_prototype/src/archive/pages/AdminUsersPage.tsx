import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Input } from "../ui";
import { ChevronLeft, Filter, Search } from "lucide-react";

function AdminUsersPage({ navigate }: { navigate: (p: Page) => void }) {
  const users = [
    { id: "u1", name: "Isabella Chen", email: "isabella@research.co", role: "user", joined: "Jun 1, 2024", status: "active", searches: 142, workspaces: 3 },
    { id: "u2", name: "Marcus Webb", email: "marcus.webb@fintech.io", role: "user", joined: "May 28, 2024", status: "active", searches: 87, workspaces: 1 },
    { id: "u3", name: "Sarah Park", email: "s.park@invest.co", role: "user", joined: "Jun 10, 2024", status: "active", searches: 203, workspaces: 5 },
    { id: "u4", name: "Admin User", email: "admin@ftd.io", role: "admin", joined: "Jan 1, 2024", status: "active", searches: 0, workspaces: 0 },
    { id: "u5", name: "David Kim", email: "d.kim@alpha.vc", role: "user", joined: "Jun 15, 2024", status: "suspended", searches: 12, workspaces: 0 },
  ];
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
          {users.map(u => (
            <div key={u.id} className="grid grid-cols-[1fr_1fr_80px_100px_80px_80px_80px] gap-4 px-4 py-3 items-center hover:bg-secondary/30 transition-all">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white text-xs font-bold shrink-0">{u.name[0]}</div>
                <span className="text-sm font-medium text-foreground truncate">{u.name}</span>
              </div>
              <span className="text-xs text-muted-foreground truncate">{u.email}</span>
              <Badge variant={u.role === "admin" ? "purple" : "neutral"} className="text-xs w-fit">{u.role}</Badge>
              <span className="text-xs text-muted-foreground">{u.joined}</span>
              <span className="font-mono text-xs text-foreground">{u.searches}</span>
              <span className="font-mono text-xs text-foreground">{u.workspaces}</span>
              <Badge variant={u.status === "active" ? "evidence" : "danger"} className="text-xs w-fit">{u.status}</Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 23: Admin System Monitor
// ────────────────────────────────────────────────

export default AdminUsersPage;
