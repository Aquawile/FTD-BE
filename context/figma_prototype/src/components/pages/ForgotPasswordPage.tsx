import { useState } from "react";
import { Page } from "../../app/types";
import { Btn, Input } from "../ui";
import { CheckCircle, ChevronLeft, Mail, Send } from "lucide-react";

function ForgotPasswordPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The API decides whether the address has an account and sends the reset email.
  const sendReset = async () => {
    setSending(true); setError(null);
    try {
      const res = await fetch("/api/auth/password-reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: email.trim() }) });
      if (!res.ok) setError("Couldn't send the reset email. Try again.");
      else if (!(await res.json()).sent) setError("No account exists for that email address.");
      else setSent(true);
    } catch {
      setError("Couldn't send the reset email. Try again.");
    } finally {
      setSending(false);
    }
  };
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
              <Input id="forgot-email" type="email" autoComplete="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />}
                onEnter={() => { if (email.includes("@") && !sending) sendReset(); }} />
            </div>
            {error && <p className="text-xs text-red-400">{error}</p>}
            <Btn variant="primary" className="w-full justify-center" onClick={sendReset} disabled={!email.includes("@") || sending}>
              <Send size={14} /> {sending ? "Sending…" : "Send Reset Link"}
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

export default ForgotPasswordPage;
