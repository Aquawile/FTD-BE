import { useState } from "react";
import { Page } from "../../app/types";
import { Btn, Input } from "../ui";
import { ArrowRight, BarChart, Eye, EyeOff, Lock, Mail, RefreshCw } from "lucide-react";
import { firebaseAuth } from "../../app/firebase";
import { browserLocalPersistence, browserSessionPersistence, setPersistence, signInWithEmailAndPassword } from "firebase/auth";

// Firebase messages are developer-facing ("Firebase: Error (auth/invalid-credential)."), so map the common ones.
function signInError(code: string | undefined): string {
  switch (code) {
    case "auth/invalid-credential":
    case "auth/wrong-password":
    case "auth/user-not-found":
      return "Email or password is incorrect.";
    case "auth/invalid-email":
      return "That email address isn't valid.";
    case "auth/too-many-requests":
      return "Too many attempts. Wait a moment or reset your password.";
    case "auth/network-request-failed":
      return "Can't reach the sign-in service. Check your connection.";
    default:
      return "Couldn't sign in. Try again.";
  }
}

function LoginPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Checked: stay signed in on this browser until you sign out (Firebase keeps refreshing the
  // 1-hour ID token in the background). Unchecked: signed out when the browser is closed.
  const [rememberMe, setRememberMe] = useState(true);

  const handleLogin = async () => {
    setLoading(true);
    setError("");
    try {
      await setPersistence(firebaseAuth, rememberMe ? browserLocalPersistence : browserSessionPersistence);
      await signInWithEmailAndPassword(firebaseAuth, email.trim(), password);
      navigate("dashboard");
    } catch (err: any) {
      setError(signInError(err?.code));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-sm space-y-6">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
          <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
        </div>
        <div>
          <h1 className="text-2xl font-bold mb-1">Sign in</h1>
          <p className="text-muted-foreground text-sm">Sign in to your research account</p>
        </div>
        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {error}
          </div>
        )}
        <form className="space-y-4" onSubmit={e => { e.preventDefault(); if (!loading) handleLogin(); }}>
          <div className="space-y-1.5">
            <label htmlFor="login-email" className="text-sm font-medium">Email address</label>
            <Input id="login-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="login-password" className="text-sm font-medium">Password</label>
            <div className="relative">
              <Input id="login-password" type={showPw ? "text" : "password"} value={password} onChange={setPassword} placeholder="Enter your password" icon={<Lock size={14} />} />
              <button type="button" onClick={() => setShowPw(p => !p)} aria-label={showPw ? "Hide password" : "Show password"} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer">
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>
          <div className="flex items-center justify-between text-sm">
            <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
              <input type="checkbox" className="rounded" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} /> Remember me
            </label>
            <button type="button" onClick={() => navigate("forgot-password")} className="text-primary hover:underline cursor-pointer text-sm">Forgot password?</button>
          </div>
          <Btn variant="primary" className="w-full justify-center" disabled={loading || !email || !password}>
            {loading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
            {loading ? "Signing in..." : "Sign In"}
          </Btn>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          No account yet?{" "}
          <button onClick={() => navigate("register")} className="text-primary hover:underline cursor-pointer">Create an account</button>
        </p>
        <p className="text-center text-xs text-muted-foreground">For research purposes only · Not investment advice</p>
      </div>
    </div>
  );
}

export default LoginPage;
