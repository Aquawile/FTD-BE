import { useState } from "react";
import { Page } from "../../app/types";
import { Btn, Input, cn } from "../ui";
import { ArrowRight, BarChart, Briefcase, Check, Hash } from "lucide-react";

function OnboardingPage({ navigate }: { navigate: (p: Page) => void }) {
  const [step, setStep] = useState(0);
  const steps = ["Welcome!", "Pick your interests", "Set up first workspace"];
  const sectors = ["Semiconductors", "AI/ML", "EV & Clean Energy", "Cloud Infrastructure", "Defense Tech", "Biotech", "Consumer Electronics", "Crypto/Blockchain"];
  const [selected, setSelected] = useState<string[]>([]);

  return (
    <div className="min-h-screen flex items-center justify-center p-8 bg-background">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center"><BarChart size={16} className="text-white" /></div>
            <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
          </div>
          <span className="text-sm text-muted-foreground">{step + 1} / {steps.length}</span>
        </div>
        <div className="flex gap-2">
          {steps.map((_, i) => <div key={i} className={cn("flex-1 h-1 rounded-full", i <= step ? "bg-primary" : "bg-secondary")} />)}
        </div>
        {step === 0 && (
          <div className="text-center space-y-4 py-4">
            <div className="text-5xl">🎉</div>
            <h1 className="text-2xl font-bold">Account verified!</h1>
            <p className="text-muted-foreground text-sm">Welcome to FTD. Let us personalize your experience in 2 quick steps.</p>
            <Btn variant="primary" size="lg" className="w-full justify-center" onClick={() => setStep(1)}>Get Started <ArrowRight size={14} /></Btn>
          </div>
        )}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">What sectors interest you?</h2>
            <p className="text-muted-foreground text-sm">Select all that apply — we will prioritize research content accordingly.</p>
            <div className="flex flex-wrap gap-2">
              {sectors.map(s => (
                <button
                  key={s}
                  onClick={() => setSelected(sel => sel.includes(s) ? sel.filter(x => x !== s) : [...sel, s])}
                  className={cn("px-3 py-1.5 rounded-lg text-sm border transition-all cursor-pointer", selected.includes(s) ? "bg-primary/15 text-primary border-primary/30" : "bg-secondary text-muted-foreground border-border hover:border-primary/20")}
                >
                  {s}
                </button>
              ))}
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={() => setStep(2)} disabled={selected.length === 0}>
              Continue ({selected.length} selected) <ArrowRight size={14} />
            </Btn>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Create your first workspace</h2>
            <p className="text-muted-foreground text-sm">Group related tickers to track them together. You can always add more later.</p>
            <div className="space-y-1.5">
              <label htmlFor="workspace-name" className="text-sm font-medium">Workspace name</label>
              <Input id="workspace-name" placeholder="e.g., AI Semiconductor Race" icon={<Briefcase size={14} />} />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="workspace-tickers" className="text-sm font-medium">Add tickers (optional)</label>
              <Input id="workspace-tickers" placeholder="NVDA, AMD, TSLA..." icon={<Hash size={14} />} />
            </div>
            <Btn variant="primary" className="w-full justify-center" onClick={() => navigate("profile")}>
              <Check size={14} /> Finish Setup
            </Btn>
            <button onClick={() => navigate("profile")} className="w-full text-center text-sm text-muted-foreground hover:text-foreground cursor-pointer">Skip for now</button>
          </div>
        )}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 7: Dashboard Home
// ────────────────────────────────────────────────

export default OnboardingPage;
