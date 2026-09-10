import { useState } from "react";
import { Page } from "../../app/types";
import { Btn } from "../ui";
import { AlertCircle, Check, CheckCircle, ChevronLeft, Info, Mail } from "lucide-react";
import { firebaseAuth } from "../../app/firebase";

function VerifyEmailPage({ navigate, userEmail }: { navigate: (p: Page) => void; userEmail?: string }) {
  const [resent, setResent] = useState(false);
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
          <div className="flex items-center gap-2"><Info size={14} className="text-blue-400" /><span>Link expires in 24 hours</span></div>
          <div className="flex items-center gap-2"><AlertCircle size={14} className="text-orange-400" /><span>Check your spam folder if not received</span></div>
        </div>
        <Btn variant="primary" className="w-full justify-center" onClick={() => navigate("profile")}>
          <Check size={14} /> I verified my email
        </Btn>
        <button
          onClick={() => setResent(true)}
          className="text-sm text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          disabled={resent}
        >
          {resent ? <span className="text-emerald-400 flex items-center gap-1 justify-center"><Check size={12} /> Email resent!</span> : "Resend verification email"}
        </button>
        <button onClick={() => navigate("login")} className="text-sm text-muted-foreground hover:text-foreground cursor-pointer flex items-center gap-1 justify-center">
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
