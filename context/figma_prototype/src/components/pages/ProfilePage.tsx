import { useState, useEffect, useRef } from "react";
import { sendPasswordResetEmail } from "firebase/auth";
import { firebaseAuth } from "../../app/firebase";
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
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [saved, setSaved] = useState(false);
  const [resetState, setResetState] = useState<"idle" | "sending" | "sent">("idle");
  const [resetError, setResetError] = useState<string | null>(null);

  const sendReset = async () => {
    setResetState("sending"); setResetError(null);
    try {
      await sendPasswordResetEmail(firebaseAuth, email);
      setResetState("sent");
    } catch {
      setResetState("idle");
      setResetError("Couldn't send the reset email. Try again.");
    }
  };

  useEffect(() => {
    try {
      const raw = localStorage.getItem("ftd_profile");
      if (raw) {
        const data = JSON.parse(raw);
        if (data.firstName) setFirstName(data.firstName);
        if (data.lastName) setLastName(data.lastName);
        if (data.photoUrl) setPhotoUrl(data.photoUrl);
      }
    } catch {}
  }, []);

  const handleSaveProfile = () => {
    try {
      localStorage.setItem("ftd_profile", JSON.stringify({ firstName, lastName, photoUrl }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };
  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Profile</h1>
      <div className="flex gap-2 mb-6 border-b border-border pb-4">
        {["profile", "security"].map(t => (
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
                  <div className="space-y-1.5"><label htmlFor="email" className="text-sm font-medium">Email address</label><div id="email" className="flex items-center gap-2 bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-muted-foreground"><Mail size={14} />{email || "—"}</div><p className="text-xs text-muted-foreground">Your sign-in email (from your account).</p></div>
                  <Btn variant="primary" size="sm" icon={<Check size={12} />} onClick={handleSaveProfile}>{saved ? "Saved" : "Save Profile"}</Btn>
                </div>
            )}
          </Card>
        </div>
      )}
      {activeTab === "security" && (
        <div className="space-y-5">
          <Card className="p-5">
            <h3 className="font-semibold mb-1">Password</h3>
            <p className="text-sm text-muted-foreground mb-4">We'll email a secure link to {email || "your address"} to set a new password.</p>
            {resetError && <p className="text-xs text-red-400 mb-3">{resetError}</p>}
            <Btn variant="primary" size="sm" icon={<Lock size={12} />} onClick={sendReset} disabled={!email || resetState === "sending"}>
              {resetState === "sent" ? "Reset link sent" : resetState === "sending" ? "Sending…" : "Email me a reset link"}
            </Btn>
          </Card>
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 20: Admin Dashboard
// ────────────────────────────────────────────────

export default ProfilePage;
