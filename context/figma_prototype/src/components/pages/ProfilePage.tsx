import { useState, useEffect, useRef } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, Card, Input, cn } from "../ui";
import { Check, Copy, Edit2, ExternalLink, Lock, Mail, RefreshCw } from "lucide-react";

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
        {["profile", "security", "preferences"].map(t => (
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
              <div className="space-y-1.5"><label className="text-sm font-medium">Current password</label>              <Input type="password" placeholder="••••••••" icon={<Lock size={14} />} /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">New password</label><Input type="password" placeholder="New password" icon={<Lock size={14} />} /></div>
              <div className="space-y-1.5"><label className="text-sm font-medium">Confirm new password</label><Input type="password" placeholder="Confirm password" icon={<Lock size={14} />} /></div>
              <Btn variant="primary" size="sm" icon={<Lock size={12} />}>Update Password</Btn>
            </div>
          </Card>
        </div>
      )}
      {activeTab === "preferences" && (
        <Card className="p-5">
          <h3 className="font-semibold mb-4">Display Preferences</h3>
          <div className="space-y-4 text-sm">
            {[
              { label: "Compact card view", desc: "Show more tickers per row", enabled: false },
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
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 20: Admin Dashboard
// ────────────────────────────────────────────────

export default ProfilePage;
