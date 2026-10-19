import { useState } from "react";
import { Page } from "../../app/types";
import { Btn, Input } from "../ui";
import { BarChart, Check, ChevronLeft, Lock, Mail, Minus, RefreshCw, UserCheck } from "lucide-react";
import { firebaseAuth } from "../../app/firebase";
import { createUserWithEmailAndPassword, sendEmailVerification } from "firebase/auth";

function RegisterPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const cred = await createUserWithEmailAndPassword(firebaseAuth, email, pw);
      await sendEmailVerification(cred.user);
      navigate("verify-email");
    } catch (err: any) {
      setError(err.message || "Failed to create account");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-sm space-y-6">
        <button onClick={() => navigate("login")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> Back to sign in</button>
        <div>
          <div className="flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <h1 className="text-2xl font-bold mb-1">Create your account</h1>
          <p className="text-muted-foreground text-sm">For research purposes only · Not investment advice</p>
        </div>
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {error}
          </div>
        )}
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label htmlFor="reg-email" className="text-sm font-medium">Email address</label>
            <Input id="reg-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="reg-password" className="text-sm font-medium">Password</label>
            <Input id="reg-password" type="password" value={pw} onChange={setPw} placeholder="Min. 8 characters" icon={<Lock size={14} />} />
          </div>
          {pw.length > 0 && (
            <div className="space-y-1">
              {[{ label: "8+ characters", ok: pw.length >= 8 }, { label: "Uppercase letter", ok: /[A-Z]/.test(pw) }, { label: "Number", ok: /[0-9]/.test(pw) }].map(r => (
                <div key={r.label} className="flex items-center gap-2 text-xs">
                  {r.ok ? <Check size={12} className="text-emerald-400" /> : <Minus size={12} className="text-muted-foreground" />}
                  <span className={r.ok ? "text-emerald-400" : "text-muted-foreground"}>{r.label}</span>
                </div>
              ))}
            </div>
          )}
          <Btn variant="primary" className="w-full justify-center" onClick={handleSubmit} disabled={!email || pw.length < 8 || loading}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <UserCheck size={14} />}
            {loading ? "Creating account..." : "Create Account"}
          </Btn>
        </div>
        <p className="text-center text-sm text-muted-foreground">Already have an account? <button onClick={() => navigate("login")} className="text-primary hover:underline cursor-pointer">Sign in</button></p>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 4: Verify Email
// ────────────────────────────────────────────────

export default RegisterPage;
