// ────────────────────────────────────────────────
// LEGACY LANDING PAGE
// ────────────────────────────────────────────────

import { useState, useEffect } from "react";
import { Card, Button as Btn, ChevronLeft, ArrowRight, BarChart2, Sparkles, TrendingUp, Users, Shield, Lock, ArrowRight, CheckCircle, Sparkles, Target, Zap, LineChart, Globe, Users, Shield, Lock } from "./ui";
import { cn } from "../utils";
import { navigate } from "../router";

interface LegacyLandingPageProps {
  navigate: (p: Page) => void;
}

export function LegacyLandingPage({ navigate }: LegacyLandingPageProps) {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center justify-center px-6 py-20 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-purple-500/5" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-from)_0%,transparent_70%)] from-primary/10 via-transparent to-transparent" />
        <div className="relative z-10 max-w-5xl mx-auto w-full text-center">
          <div className="mb-8 flex items-center justify-center">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <BarChart2 size={32} className="text-primary" />
            </div>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-r from-foreground via-primary to-purple-500 bg-clip-text text-transparent">
            Financial Intelligence<br />Powered by Evidence
          </h1>
          <p className="text-xl md:text-xl max-w-3xl mx-auto text-muted-foreground mb-10 leading-relaxed">
            Transform market noise into actionable intelligence. FTD combines SEC filings, news sentiment, 
            and community signals into hype vs. evidence scores — so you can separate signal from noise.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
            <button
              onClick={() => navigate("register")}
              className="group w-full sm:w-auto px-8 py-4 rounded-xl bg-primary text-primary-foreground font-semibold text-lg shadow-lg hover:shadow-primary/30 transition-all duration-200 flex items-center gap-2"
            >
              <Sparkles size={18} /> Get Started Free
            </button>
            <button
              onClick={() => navigate("login")}
              className="border border-border bg-background hover:bg-secondary text-foreground px-8 py-4 rounded-xl font-semibold transition-all duration-200 hover:bg-secondary/50"
            >
              Sign In
            </button>
          </div>

          <div className="mt-16 flex items-center justify-center gap-8 text-muted-foreground text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-400" />
              <span>No credit card required</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-emerald-400" />
              <span>SOC2 compliant</span>
            </div>
          </div>
        </div>
      </section>

      {/* Trust Indicators */}
      <section className="py-16 border-y border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-center justify-between flex-wrap gap-8 text-center">
            {[
              { label: "1.1M+", label2: "Articles Processed" },
              { label: "494", label2: "Tracked Tickers" },
              { label: "99.9%", label2: "Uptime SLA" },
              { label: "84%", label2: "Avg Evidence Score" },
            ].map((item, i) => (
              <div key={i} className="flex flex-col items-center">
                <div className="text-4xl font-bold font-mono text-foreground">{item[0]}</div>
                <div className="text-muted-foreground text-sm">{item[1]}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Highlights */}
      <section className="py-20 bg-secondary/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
              <Sparkles size={14} /> Why FTD?
            </span>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight mb-4">Built Different</h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Every feature is designed to separate signal from noise — so you make decisions based on evidence, not hype.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 mt-16">
            {[
              {
                icon: Target,
                title: "Hype vs Evidence Scoring",
                desc: "Every ticker gets dual scores — community hype vs. fundamental evidence — so you know what's real vs. what's hype.",
                icon: <Target size={24} />,
              },
              {
                icon: Sparkles,
                title: "AI-Powered Research",
                desc: "Automated SEC filing analysis, news sentiment, community sentiment, and filing summarization — all in one view.",
                icon: <Sparkles />,
              },
              {
                icon: Target,
                title: "Source-Verified Data",
                desc: "Every claim links back to SEC filings, SEC EDGAR, Reddit, news wires — no black boxes.",
                icon: <Target />,
              },
            ].map((f, i) => (
              <Card key={i} className="p-6 h-full hover:border-primary/30 transition-colors">
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                  <f.icon size={24} className="text-primary" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{f.title}</h2>
                <p className="text-muted-foreground leading-relaxed">{f.desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials / Social Proof */}
      <section className="py-20 bg-secondary/30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-12">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
              <Sparkles size={14} /> Trusted by Analysts & Investors
            </span>
            <h2 className="text-4xl font-bold mb-4">What Our Users Say</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { quote: "The hype vs evidence scoring completely changed how I evaluate positions. I avoided three bad trades last quarter alone.", author: "M. Chen", role: "Portfolio Manager", company: "Apex Capital" },
              { quote: "Finally, a tool that doesn't just show me news — it tells me what's actually backed by filings vs. what's just Reddit hype.", author: "J. Rodriguez", role: "Senior Analyst", company: "Meridian Funds" },
              { quote: "The SEC filing summaries save me hours every week. I can review 10-Ks in minutes instead of hours.", author: "S. Kim", role: "Research Analyst", company: "Vantage Point" },
            ].map((t, i) => (
              <Card key={i} className="p-6 h-full hover:border-primary/30 transition-colors">
                <div className="flex gap-2 mb-3">
                  <div className="w-2 h-2 rounded-full bg-primary" />
                  <div className="w-2 h-2 rounded-full bg-primary/50" />
                  <div className="w-2 h-2 rounded-full bg-primary/25" />
                </div>
                <p className="text-lg leading-relaxed mb-4">"{t.quote}"</p>
                <div className="flex items-center gap-2 mt-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="font-medium text-sm text-primary">{t.author[0]}</span>
                  </div>
                  <div>
                    <p className="font-medium text-sm">{t.author}</p>
                    <p className="text-xs text-muted-foreground">{t.role} · {t.company}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-gradient-to-br from-primary/10 via-background to-purple-500/5">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Sparkles size={14} /> Ready to trade on evidence, not hype?
          </div>
          <h2 className="text-4xl md:text-5xl font-bold mb-6">Start Making Evidence-Based Decisions Today</h2>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Join 1,200+ analysts and investors who've stopped guessing and started investing with evidence.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate("register")}
              className="group w-full sm:w-auto px-8 py-4 rounded-xl bg-primary text-primary-foreground font-semibold text-lg shadow-lg hover:shadow-primary/30 transition-all duration-200 flex items-center gap-2"
            >
              <Sparkles size={18} /> Get Started Free
            </button>
            <button
              onClick={() => navigate("login")}
              className="border border-border bg-background hover:bg-secondary text-foreground px-8 py-4 rounded-xl font-semibold transition-all duration-200 hover:bg-secondary/50"
            >
              Sign In
            </button>
          </div>
          <p className="mt-8 text-sm text-muted-foreground">
            No credit card required · 14-day free trial · Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-border">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-10">
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <BarChart2 size={24} className="text-primary" />
                <span className="font-bold text-xl tracking-tight" style={{ fontFamily: "'Outfit', sans-serif" }}>FTD</span>
              </div>
              <p className="text-muted-foreground text-sm max-w-xs">Financial intelligence powered by evidence. Separate signal from noise.</p>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Product</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">Dashboard</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Search</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Alerts</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Workspaces</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Company</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">About</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Careers</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Press</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-3">Legal</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Terms</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Security</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Cookies</a></li>
              </ul>
            </div>
          </div>
          <div className="flex items-center justify-between border-t border-border pt-8">
            <p className="text-sm text-muted-foreground">© 2024 FTD. All rights reserved.</            </p>
            <div className="flex items-center gap-6">
              <a href="#" className="text-muted-foreground hover:text-foreground transition-colors"><Twitter size={16} /></a>
              <a href="#" className="text-muted-foreground hover:text-foreground transition-colors"><Linkedin size={16} /></a>
              <a href="#" className="text-muted-foreground hover:text-foreground transition-colors"><Github size={16} /></a>
              <a href="#" className="text-muted-foreground hover:text-foreground transition-colors"><Discord size={16} /></a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default LegacyLandingPage;