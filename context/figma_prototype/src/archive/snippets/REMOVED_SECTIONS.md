# Removed live-page sections (archived 2026-10-16)

Exact source removed from live pages because it displayed data no API provides
(hype/evidence scores, hardcoded numbers, random sparklines, fake sessions/keys)
or linked to archived pages. Each block notes its original file; paste it back
and re-add any imports listed at the top of that file in git history
(`git show hotfix/relational-data-sync:context/figma_prototype/src/<path>`).

## NewsArticle_interface

From `src/components/pages/TickerDashboard.tsx`

```tsx
interface NewsArticle {
  id: number;
  ticker: string;
  headline: string;
  source: string;
  time: string;
  summary: string;
  hype: number;
  evidence: number;
  claims: string[];
  evidenceLinks: string[];
  flagged: boolean;
}
```

## flagArticle

From `src/components/pages/TickerDashboard.tsx`

```tsx
  const flagArticle = (id: number) => setArticles(prev => prev.map(a => a.id === id ? { ...a, flagged: !a.flagged } : a));
```

## NASDAQ_badge_hardcoded

From `src/components/pages/TickerDashboard.tsx`

```tsx
                <Badge variant="neutral">NASDAQ</Badge>
```

## Compare_button

From `src/components/pages/TickerDashboard.tsx`

```tsx
              <Btn variant="secondary" size="sm" icon={<Maximize2 size={12} />} onClick={() => navigate("ticker-comparison")}>Compare</Btn>
```

## ScorePills

From `src/components/pages/TickerDashboard.tsx`

```tsx
            <div className="flex items-center gap-6">
              <ScorePill label="Hype Score" score={t.hype_score} type="hype" />
              <ScorePill label="Evidence Score" score={t.evidence_score} type="evidence" />
            </div>
```

## ExportReport_button

From `src/components/pages/TickerDashboard.tsx`

```tsx
                  <Btn variant="secondary" size="sm" className="w-full" icon={<Download size={12} />} onClick={() => navigate("ticker-comparison")}>Export Report</Btn>
```

## MockArticleCards

From `src/components/pages/TickerDashboard.tsx`

```tsx
            ) : (
              articles.map(a => (
                <Card key={a.id} className="p-5">
                  <div className="flex items-start gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="neutral" className="text-xs">{a.source}</Badge>
                        <span className="text-xs text-muted-foreground">{a.time}</span>
                        {a.flagged && <Badge variant="hype" className="text-xs"><Flag size={8} /> Reported</Badge>}
                      </div>
                      <h4 className="font-semibold text-sm text-foreground mb-2 leading-snug">{a.headline}</h4>
                      <p className="text-xs text-muted-foreground leading-relaxed">{a.summary}</p>
                      {a.claims.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {a.claims.map(c => <Badge key={c} variant="outline" className="text-xs">{c}</Badge>)}
                        </div>
                      )}
                      {a.evidenceLinks.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {a.evidenceLinks.map(l => <Badge key={l} variant="evidence" className="text-xs"><ExternalLink size={8} /> {l}</Badge>)}
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-2 shrink-0">
                      <div className="text-right space-y-1">
                        <div className="text-xs text-muted-foreground">Hype</div>
                        <div className="font-mono text-sm font-bold" style={{ color: getHypeColor(a.hype) }}>{a.hype}</div>
                      </div>
                      <div className="text-right space-y-1">
                        <div className="text-xs text-muted-foreground">Evidence</div>
                        <div className="font-mono text-sm font-bold" style={{ color: getEvidenceColor(a.evidence) }}>{a.evidence}</div>
                      </div>
                      <button
                        onClick={() => { flagArticle(a.id); onReport(); }}
                        className={cn("mt-2 p-2 rounded-lg border transition-all cursor-pointer", a.flagged ? "bg-orange-500/15 border-orange-500/30 text-orange-400" : "border-border text-muted-foreground hover:text-orange-400 hover:border-orange-500/30")}
                      >
                        <Flag size={13} />
                      </button>
                    </div>
                  </div>
                </Card>
              ))
```

## EvidenceMatrixTab

From `src/components/pages/TickerDashboard.tsx`

```tsx
        {tab === "evidence" && (
          <div className="space-y-5">
            <Card className="p-5">
              <h3 className="font-semibold mb-4">Evidence Breakdown Matrix</h3>
              <div className="space-y-4">
                {[
                  { category: "SEC Filings & XBRL Data", score: 94, count: "12 filings", description: "All major financial disclosures verified and parsed. Revenue, margin, and segment data fully corroborated." },
                  { category: "Analyst Reports", score: 72, count: "28 reports", description: "Sell-side consensus moderately evidenced. Price targets range 20–150% above current price with mixed backing." },
                  { category: "News Articles", score: 61, count: "847 articles", description: "Mainstream financial news mostly factual with selective embellishment in headlines." },
                  { category: "Community / Reddit", score: 23, count: "2,341 posts", description: "Heavy speculative content. Most high-engagement posts lack quantitative financial evidence." },
                ].map(e => (
                  <div key={e.category} className="p-4 bg-secondary/30 rounded-xl border border-border/50">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="font-medium text-sm text-foreground">{e.category}</span>
                        <span className="text-xs text-muted-foreground ml-2">{e.count}</span>
                      </div>
                      <span className="font-mono font-bold text-sm" style={{ color: getEvidenceColor(e.score) }}>{e.score}/100</span>
                    </div>
                    <div className="h-2 rounded-full bg-secondary overflow-hidden mb-2">
                      <div className="h-full rounded-full transition-all" style={{ width: `${e.score}%`, background: getEvidenceColor(e.score) }} />
                    </div>
                    <p className="text-xs text-muted-foreground">{e.description}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}
```

## Dashboard_AskAI_button

From `src/components/pages/DashboardPage.tsx`

```tsx
        <Btn variant="primary" onClick={() => navigate("chat")} icon={<MessageSquare size={14} />}>Ask AI</Btn>
```

## Dashboard_topMovers_firstFive

From `src/components/pages/DashboardPage.tsx`

```tsx
  const topMovers = trackedTickers.slice(0, 5);
  const spData = [45, 52, 48, 63, 71, 68, 74, 69, 77, 82, 79, 84];
```

## Dashboard_divergence_title

From `src/components/pages/DashboardPage.tsx`

```tsx
            <h2 className="font-semibold text-foreground">Top Hype/Evidence Divergence</h2>
```

## Dashboard_score_line

From `src/components/pages/DashboardPage.tsx`

```tsx
                    <div className="mt-1.5 flex items-center gap-3">
                      <div className="text-xs text-muted-foreground">
                        Evidence: {t.evidence_score ?? "—"} | Hype: {t.hype_score ?? "—"}
                      </div>
                    </div>
```

## Dashboard_random_sparkline

From `src/components/pages/DashboardPage.tsx`

```tsx
                  <Sparkline data={spData.map(v => v + Math.random() * 8 - 4)} color={changePct > 0 ? "#10B981" : "#EF4444"} />
```

## Dashboard_AIChatCard

From `src/components/pages/DashboardPage.tsx`

```tsx
      {/* AI chat preview */}
      <Card className="p-5 border-primary/20 bg-gradient-to-r from-primary/5 to-accent/5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-purple-500/15 flex items-center justify-center">
            <Sparkles size={18} className="text-purple-400" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm text-foreground">AI Research Assistant</h3>
            <p className="text-xs text-muted-foreground">Ask complex multi-ticker questions. Sources always cited.</p>
          </div>
          <Btn variant="primary" size="sm" onClick={() => navigate("chat")} icon={<MessageSquare size={12} />}>Open Chat</Btn>
        </div>
      </Card>
```

## Search_sort_logic

From `src/components/pages/SearchPage.tsx`

```tsx
    if (sortBy === "hype") return (b.hype_score ?? 0) - (a.hype_score ?? 0);
    if (sortBy === "evidence") return (b.evidence_score ?? 0) - (a.evidence_score ?? 0);
    return (b.hype_score ?? 0) - (a.hype_score ?? 0) - (b.evidence_score ?? 0) + (a.evidence_score ?? 0);
```

## Search_sort_options

From `src/components/pages/SearchPage.tsx`

```tsx
            <option value="divergence">Hype/Evidence Gap</option>
            <option value="highest-hype">Highest Hype</option>
            <option value="highest-evidence">Highest Evidence</option>
```

## Workspace_hardcoded_stat_cards

From `src/components/pages/WorkspaceDetailPage.tsx`

```tsx
          { label: "Avg Hype Score", value: "82", color: "#F59E0B" },
          { label: "Avg Evidence Score", value: "66", color: "#10B981" },
          { label: "Active Alerts", value: "3", color: "#3B88F6" },
```

## Login_hero_stats_hardcoded

From `src/components/pages/LoginPage.tsx`

```tsx
          <div className="mt-8 flex gap-4">
            {[{ n: "2.4M+", l: "Articles Analyzed" }, { n: "180K+", l: "Filings Indexed" }, { n: "94%", l: "Mapping Accuracy" }].map(s => (
              <div key={s.l}>
                <div className="font-mono font-bold text-lg text-primary">{s.n}</div>
                <div className="text-xs text-muted-foreground">{s.l}</div>
              </div>
            ))}
          </div>
```

## Login_admin_link

From `src/components/pages/LoginPage.tsx`

```tsx
          {/* Admin shortcut */}
          <p className="text-center text-xs text-muted-foreground/50">
            <button onClick={() => { navigate("admin"); }} className="hover:text-muted-foreground cursor-pointer">Admin access →</button>
          </p>
```

## Profile_active_sessions_hardcoded

From `src/components/pages/ProfilePage.tsx`

```tsx
          <Card className="p-5">
            <h3 className="font-semibold mb-2">Active Sessions</h3>
            <p className="text-xs text-muted-foreground mb-4">Manage devices where you are currently signed in.</p>
            {[{ device: "MacBook Pro · Chrome", location: "San Francisco, CA", time: "Current session", current: true }, { device: "iPhone 15 · Safari", location: "San Francisco, CA", time: "2 days ago", current: false }].map(s => (
              <div key={s.device} className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
                <div>
                  <div className="text-sm font-medium text-foreground">{s.device}</div>
                  <div className="text-xs text-muted-foreground">{s.location} · {s.time}</div>
                </div>
                {s.current ? <Badge variant="evidence">Active</Badge> : <Btn variant="ghost" size="sm" className="text-red-400">Revoke</Btn>}
              </div>
            ))}
          </Card>
```

## Profile_evidence_pref

From `src/components/pages/ProfilePage.tsx`

```tsx
              { label: "Show evidence score by default", desc: "Prioritize evidence over hype display", enabled: true },
```

## WorkspaceSettings_hype_toggles_1

From `src/components/pages/WorkspaceSettingsPage.tsx`

```tsx
              { label: "Narrative shift alerts", desc: "Notify when Hype/Evidence delta changes ≥10 points", enabled: true },
```

## WorkspaceSettings_hype_toggles_2

From `src/components/pages/WorkspaceSettingsPage.tsx`

```tsx
              { label: "Reddit hype spikes", desc: "Alert when post volume increases >200% in 4 hours", enabled: false },
```

## Profile_api_key_tab_fake

From `src/components/pages/ProfilePage.tsx`

```tsx
      {activeTab === "api" && (
        <Card className="p-5">
          <h3 className="font-semibold mb-2">API Access</h3>
          <p className="text-xs text-muted-foreground mb-4">Use the FTD API to programmatically access research data and scores.</p>
          <div className="p-3 bg-secondary/50 rounded-lg border border-border font-mono text-xs text-muted-foreground mb-3 flex items-center justify-between">
            <span>ftd_beta_••••••••••••••••••••</span>
            <button className="text-primary hover:underline cursor-pointer flex items-center gap-1"><Copy size={10} /> Copy</button>
          </div>
          <div className="flex gap-2">
            <Btn variant="secondary" size="sm" icon={<RefreshCw size={12} />}>Regenerate Key</Btn>
            <Btn variant="ghost" size="sm" icon={<ExternalLink size={12} />}>API Docs</Btn>
          </div>
        </Card>
      )}
```

## Sidebar_alerts_badge_hardcoded

From `src/components/Shell.tsx` (sidebar nav item)

```tsx
              {!collapsed && item.id === "alerts" && <span className="ml-auto text-xs bg-orange-500 text-white rounded-full px-1.5 py-0.5 font-mono">2</span>}
```
