import { useState } from "react";
import { Page } from "../../app/types";
import { Btn, Input } from "../ui";
import { ArrowRight, BarChart, Eye, EyeOff, Globe, Lock, Mail, RefreshCw } from "lucide-react";
import { firebaseAuth } from "../../app/firebase";
import { signInWithEmailAndPassword } from "firebase/auth";

function LoginPage({ navigate }: { navigate: (p: Page) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [rememberMe, setRememberMe] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    setError("");
    try {
       await signInWithEmailAndPassword(firebaseAuth, email, password);
       navigate("search");
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 bg-gradient-to-br from-primary/10 to-secondary p-12 border-r border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
          <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
        </div>
        <div>
          <div className="text-4xl font-bold mb-4 leading-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Research with<br />
            <span style={{ color: "#10B981" }}>evidence.</span><br />
            Not noise.
          </div>
          <p className="text-muted-foreground text-sm leading-relaxed max-w-sm">
            The platform that turns raw financial data into verifiable insight — with AI scoring every claim on an evidence scale.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">Not investment advice · For research purposes only</div>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm space-y-6">
          <div className="lg:hidden flex items-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <div>
            <h1 className="text-2xl font-bold mb-1">Welcome back</h1>
            <p className="text-muted-foreground text-sm">Sign in to your research account</p>
            <p className="text-sm text-muted-foreground mt-2">
              Don't have an account? <button onClick={() => navigate("register")} className="text-primary hover:underline cursor-pointer">Create one free</button>
            </p>
          </div>
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
              {error}
            </div>
          )}
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="login-email" className="text-sm font-medium">Email address</label>
                <Input id="login-email" type="email" value={email} onChange={setEmail} placeholder="you@example.com" icon={<Mail size={14} />} />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="login-password" className="text-sm font-medium">Password</label>
                  <div className="relative">                  <Input id="login-password" type={showPw ? "text" : "password"} value={password} onChange={setPassword} placeholder="Enter your password" icon={<Lock size={14} />} />
                <button onClick={() => setShowPw(p => !p)} className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer">
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer text-muted-foreground">
                <input type="checkbox" className="rounded" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} /> Remember me
              </label>
              <button onClick={() => navigate("forgot-password")} className="text-primary hover:underline cursor-pointer text-sm">Forgot password?</button>
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={handleLogin} disabled={loading}>
              {loading ? <RefreshCw size={14} className="animate-spin" /> : <ArrowRight size={14} />}
              {loading ? "Signing in..." : "Sign In"}
            </Btn>
          </div>
          <div className="relative"><div className="absolute inset-0 flex items-center"><div className="w-full border-t border-border" /></div><div className="relative flex justify-center text-xs text-muted-foreground"><span className="bg-background px-3">or continue with</span></div></div>
          <Btn variant="outline" className="w-full justify-center" onClick={handleLogin}>
            <Globe size={14} /> Google
          </Btn>
          <p className="text-center text-sm text-muted-foreground">
            No account yet?{" "}
            <button onClick={() => navigate("register")} className="text-primary hover:underline cursor-pointer">Create one free</button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 3: Register
// ────────────────────────────────────────────────

export default LoginPage;
