import { useState, useEffect, useRef } from "react";
import { EmailAuthProvider, deleteUser, reauthenticateWithCredential, updateProfile } from "firebase/auth";
import { firebaseAuth } from "../../app/firebase";
import { Page } from "../../app/types";
import { Btn, Card, Input, Modal, cn, initialsOf } from "../ui";
import { deleteAccountRecord, saveAvatar } from "../../api";
import { Check, Edit2, Lock, Mail, Trash2 } from "lucide-react";

// Shrink an uploaded image to a small JPEG data URL; it is saved with the account.
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

function ProfilePage({ navigate, userEmail, userName, userPermissions, loading, onProfileUpdated, avatarUrl, onAvatarChanged }: { navigate: (p: Page) => void; userEmail?: string; userName?: string; userPermissions?: string[]; loading?: boolean; onProfileUpdated?: () => void; avatarUrl?: string | null; onAvatarChanged?: (url: string) => void }) {
  const [activeTab, setActiveTab] = useState("profile");
  const user = firebaseAuth.currentUser;
  const email = userEmail || "";
  // The username is the Firebase account's displayName, so it follows you to any device.
  const [username, setUsername] = useState(user?.displayName || userName || "");
  const displayName = username.trim() || userName || "";
  const initials = initialsOf(displayName);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [resetState, setResetState] = useState<"idle" | "sending" | "sent">("idle");
  const [resetError, setResetError] = useState<string | null>(null);

  // Delete account: two confirmations, then the password again (Firebase asks for a recent sign-in).
  const [deleteStep, setDeleteStep] = useState<0 | 1 | 2>(0);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteTyped, setDeleteTyped] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const closeDelete = () => { setDeleteStep(0); setDeletePassword(""); setDeleteTyped(""); setDeleteError(null); };

  const deleteAccount = async () => {
    if (!user || !user.email) return;
    setDeleting(true); setDeleteError(null);
    try {
      await reauthenticateWithCredential(user, EmailAuthProvider.credential(user.email, deletePassword));
    } catch {
      setDeleteError("That password isn't right. Your account was not deleted.");
      setDeleting(false);
      return;
    }
    try {
      await deleteAccountRecord(user);          // database side: archived and detached, not erased
      await deleteUser(user);                   // Firebase side: the account record is removed
      // Firebase now reports no user, so the app returns to the sign-in page on its own.
    } catch (e: any) {
      setDeleteError(e?.message || "Couldn't delete your account. Try again.");
      setDeleting(false);
    }
  };

  const sendReset = async () => {
    setResetState("sending"); setResetError(null);
    try {
      const res = await fetch("/api/auth/password-reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email }) });
      if (!res.ok || !(await res.json()).sent) throw new Error("reset");
      setResetState("sent");
    } catch {
      setResetState("idle");
      setResetError("Couldn't send the reset email. Try again.");
    }
  };

  // The photo is saved with the account (not in this browser), so it is there on every sign-in.
  const handlePhoto = async (file: File | undefined) => {
    if (!file || !user) return;
    setProfileError(null);
    let dataUrl: string;
    try {
      dataUrl = await shrinkImage(file);
    } catch {
      setProfileError("Couldn't read that image.");
      return;
    }
    try {
      await saveAvatar(user, dataUrl);
      onAvatarChanged?.(dataUrl);
    } catch (e: any) {
      setProfileError(e?.message || "Couldn't save your photo.");
    }
  };

  const handleSaveProfile = async () => {
    if (!user) return;
    const name = username.trim();
    if (name.length < 2 || name.length > 30) { setProfileError("Username must be 2 to 30 characters."); return; }
    setSaving(true); setProfileError(null);
    try {
      await updateProfile(user, { displayName: name });
      await user.reload();
      onProfileUpdated?.();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setProfileError("Couldn't save your username. Try again.");
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
                {avatarUrl ? <img src={avatarUrl} alt="Profile" className="w-full h-full object-cover" /> : initials}
              </div>
              <div>
                <div className="font-semibold text-lg">{displayName || "User"}</div>
                <div className="text-muted-foreground text-sm">{email || "—"}</div>
              </div>
              <Btn variant="secondary" size="sm" className="ml-auto" icon={<Edit2 size={12} />} onClick={() => fileInputRef.current?.click()}>Edit Photo</Btn>
              <input ref={fileInputRef} type="file" accept="image/*" aria-label="Upload profile photo" className="hidden" onChange={e => handlePhoto(e.target.files?.[0])} />
            </div>
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : (
                <div className="space-y-3">
                  <div className="space-y-1.5"><label htmlFor="username" className="text-sm font-medium">Username</label><Input id="username" value={username} onChange={setUsername} placeholder="Choose a username" autoComplete="username" onEnter={handleSaveProfile} /><p className="text-xs text-muted-foreground">Shown in the top bar and your account menu.</p></div>
                  <div className="space-y-1.5"><span id="email-label" className="block text-sm font-medium">Email address</span><div role="group" aria-labelledby="email-label" className="flex items-center gap-2 bg-input-background border border-border rounded-lg px-3 py-2 text-sm text-muted-foreground"><Mail size={14} />{email || "—"}</div><p className="text-xs text-muted-foreground">Your sign-in email (from your account).</p></div>
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
          <Card className="p-5 border-red-500/30">
            <h3 className="font-semibold mb-1 text-red-400">Danger zone</h3>
            <p className="text-sm text-muted-foreground mb-4">Deleting your account signs you out for good and removes your sign-in. Your workspaces are archived and your alerts stop. This can't be undone.</p>
            <Btn variant="secondary" size="sm" className="border-red-500/30 text-red-400 hover:bg-red-500/10" icon={<Trash2 size={12} />} onClick={() => setDeleteStep(1)}>Delete my account</Btn>
          </Card>
        </div>
      )}
      {deleteStep === 1 && (
        <Modal title="Delete your account?" onClose={closeDelete}>
          <p className="text-sm text-muted-foreground mb-4">You are about to delete the account for {email}. You will lose access to your workspaces and alerts.</p>
          <div className="flex gap-2 justify-end">
            <Btn variant="secondary" onClick={closeDelete}>Cancel</Btn>
            <Btn variant="danger" onClick={() => setDeleteStep(2)}>Yes, continue</Btn>
          </div>
        </Modal>
      )}
      {deleteStep === 2 && (
        <Modal title="Are you absolutely sure?" onClose={deleting ? () => undefined : closeDelete}>
          <p className="text-sm text-muted-foreground mb-3">This is permanent. Type <span className="font-mono text-foreground">DELETE</span> and enter your password to confirm.</p>
          <div className="space-y-3 mb-4">
            <Input id="delete-confirm" ariaLabel="Type DELETE to confirm" value={deleteTyped} onChange={setDeleteTyped} placeholder="DELETE" />
            <Input id="delete-password" ariaLabel="Your password" type="password" autoComplete="current-password" value={deletePassword} onChange={setDeletePassword} placeholder="Password" onEnter={() => { if (deleteTyped === "DELETE" && deletePassword && !deleting) deleteAccount(); }} />
          </div>
          {deleteError && <p className="text-xs text-red-400 mb-3">{deleteError}</p>}
          <div className="flex gap-2 justify-end">
            <Btn variant="secondary" onClick={closeDelete} disabled={deleting}>Cancel</Btn>
            <Btn variant="danger" onClick={deleteAccount} disabled={deleting || deleteTyped !== "DELETE" || !deletePassword} icon={<Trash2 size={12} />}>{deleting ? "Deleting…" : "Delete my account"}</Btn>
          </div>
        </Modal>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 20: Admin Dashboard
// ────────────────────────────────────────────────

export default ProfilePage;
