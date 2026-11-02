import { useState } from "react";
import { Page } from "../../app/types";
import { Btn } from "../ui";
import { AlertCircle, Check, CheckCircle, ChevronLeft, Mail } from "lucide-react";
import { firebaseAuth } from "../../app/firebase";
import { sendEmailVerification, signOut } from "firebase/auth";

function VerifyEmailPage({ navigate, userEmail, onVerified }: { navigate: (p: Page) => void; userEmail?: string; onVerified?: () => void }) {
  const [resent, setResent] = useState(false);
  const [resendError, setResendError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);
  const [notVerified, setNotVerified] = useState<string | null>(null);

  const resend = async () => {
    const user = firebaseAuth.currentUser;
    if (!user) { setResendError("Sign in again to resend the email."); return; }
    setResendError(null);
    try {
      await sendEmailVerification(user);
      setResent(true);
    } catch (e: any) {
      setResendError(e?.code === "auth/too-many-requests" ? "Too many requests. Wait a few minutes and try again." : "Couldn't resend the email. Try again.");
    }
  };

  // Re-read the live status from Firebase (and refresh the ID token, whose email_verified claim the API checks).
  const continueToApp = async () => {
    const user = firebaseAuth.currentUser;
    if (!user) { navigate("login"); return; }
    setChecking(true);
    setNotVerified(null);
    try {
      await user.reload();
      await user.getIdToken(true);
    } catch {
      setNotVerified("Couldn't check your verification status. Check your connection and try again.");
      setChecking(false);
      return;
    }
    setChecking(false);
    if (!firebaseAuth.currentUser?.emailVerified) {
      setNotVerified("Your email isn't verified yet. Open the link we sent you, then press the button again.");
      return;
    }
    onVerified?.();
    navigate("dashboard");
  };

  const backToSignIn = async () => {
    try { await signOut(firebaseAuth); } catch { /* already signed out */ }
    navigate("login");
  };
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
          <div className="flex items-center gap-2"><AlertCircle size={14} className="text-orange-400" /><span>Check your spam folder if not received</span></div>
        </div>
        <Btn variant="primary" className="w-full justify-center" onClick={continueToApp} disabled={checking}>
          <Check size={14} /> {checking ? "Checking..." : "I verified my email"}
        </Btn>
        {notVerified && <p role="alert" className="text-sm text-orange-400">{notVerified}</p>}
        <button
          onClick={resend}
          className="text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          disabled={resent}
        >
          {resent ? <span className="text-emerald-400 flex items-center gap-1 justify-center"><Check size={12} /> Email resent!</span> : "Resend verification email"}
        </button>
        {resendError && <p className="text-xs text-red-400">{resendError}</p>}
        <button onClick={backToSignIn} className="text-sm text-muted-foreground hover:text-foreground cursor-pointer flex items-center gap-1 justify-center">
          <ChevronLeft size={14} /> Back to sign in
        </button>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 5: Forgot Password
// ────────────────────────────────────────────────

export default VerifyEmailPage;
