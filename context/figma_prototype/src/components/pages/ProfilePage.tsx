import { useState, useEffect, useRef } from "react";
import { sendPasswordResetEmail, updateProfile } from "firebase/auth";
import { firebaseAuth } from "../../app/firebase";
import { Page } from "../../app/types";
import { Btn, Card, Input, cn } from "../ui";
import { Check, Edit2, Lock, Mail } from "lucide-react";

const photoKey = (uid: string) => `ftd.profilePhoto.${uid}`;

// Shrink an uploaded image to a small JPEG data URL so it can be kept on this device.
function shrinkImage(file: File, size = 160): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const scale = Math.min(1, size / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);
      canvas.getContext("2d")?.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      resolve(canvas.toDataURL("image/jpeg", 0.85));
    };
    img.onerror = reject;
    img.src = URL.createObjectURL(file);
  });
}

function ProfilePage({ navigate, userEmail, userName, userPermissions, loading, onProfileUpdated }: { navigate: (p: Page) => void; userEmail?: string; userName?: string; userPermissions?: string[]; loading?: boolean; onProfileUpdated?: () => void }) {
  const [activeTab, setActiveTab] = useState("profile");
  const user = firebaseAuth.currentUser;
  const email = userEmail || "";
  // The name lives on the Firebase account (displayName), so it follows you to any device.
  const accountName = user?.displayName || "";
  const [firstName, setFirstName] = useState(accountName.split(" ")[0] || "");
  const [lastName, setLastName] = useState(accountName.split(" ").slice(1).join(" ") || "");
  const displayName = [firstName, lastName].filter(Boolean).join(" ") || userName || "";
  const initials = displayName.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "??";
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
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

  // Photo: kept on this device (there is no file storage for profile photos).
  useEffect(() => {
    if (!user) return;
    try { setPhotoUrl(localStorage.getItem(photoKey(user.uid))); } catch { /* storage unavailable */ }
  }, [user?.uid]);

  const handlePhoto = async (file: File | undefined) => {
    if (!file || !user) return;
    try {
      const dataUrl = await shrinkImage(file);
      setPhotoUrl(dataUrl);
      try { localStorage.setItem(photoKey(user.uid), dataUrl); } catch { /* storage full or blocked */ }
    } catch {
      setProfileError("Couldn't read that image.");
    }
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    setSaving(true); setProfileError(null);
    try {
      await updateProfile(user, { displayName: [firstName.trim(), lastName.trim()].filter(Boolean).join(" ") || null });
      await user.reload();
      onProfileUpdated?.();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setProfileError("Couldn't save your name. Try again.");
    } finally {
      setSaving(false);
    }
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
                <div className="text-muted-foreground text-sm">{email || "—"}</div>
              </div>
              <Btn variant="secondary" size="sm" className="ml-auto" icon={<Edit2 size={12} />} onClick={() => fileInputRef.current?.click()}>Edit Photo</Btn>
              <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={e => handlePhoto(e.target.files?.[0])} />
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
                  {profileError && <p className="text-xs text-red-400">{profileError}</p>}
                  <Btn variant="primary" size="sm" icon={<Check size={12} />} onClick={handleSaveProfile} disabled={saving}>{saved ? "Saved" : saving ? "Saving…" : "Save Profile"}</Btn>
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
