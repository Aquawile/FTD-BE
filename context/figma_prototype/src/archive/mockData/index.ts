/* ============================================================
   MOCK DATA - PRESERVED FOR REFERENCE
   These constants are not rendered in the active UI. They are
   preserved as fallback data for development without a backend.
   ============================================================ */

export const TICKERS = [
  { symbol: "NVDA", name: "NVIDIA Corporation", hype: 84, evidence: 71, sector: "Semiconductors", change: -1.51, price: 217.44 },
  { symbol: "TSLA", name: "Tesla, Inc.", hype: 91, evidence: 48, sector: "Automotive / EV", change: -3.22, price: 356.09 },
  { symbol: "AAPL", name: "Apple Inc.", hype: 62, evidence: 88, sector: "Consumer Electronics", change: +2.61, price: 325.13 },
  { symbol: "MSFT", name: "Microsoft Corporation", hype: 58, evidence: 85, sector: "Cloud / AI", change: -1.24, price: 501.02 },
  { symbol: "AMD", name: "Advanced Micro Devices", hype: 76, evidence: 65, sector: "Semiconductors", change: -2.36, price: 459.61 },
  { symbol: "PLTR", name: "Palantir Technologies", hype: 88, evidence: 52, sector: "AI / Defense", change: -3.47, price: 179.92 },
  { symbol: "META", name: "Meta Platforms", hype: 67, evidence: 73, sector: "Social / AI", change: +1.08, price: 578.54 },
  { symbol: "GOOG", name: "Alphabet Inc.", hype: 61, evidence: 80, sector: "Search / Cloud", change: -1.01, price: 332.03 },
  { symbol: "GOOGL", name: "Alphabet Inc. Class A", hype: 61, evidence: 80, sector: "Search / Cloud", change: -1.28, price: 335.02 },
  { symbol: "AMZN", name: "AMZN", hype: 67, evidence: 73, sector: "E-commerce / Cloud", change: -1.87, price: 254.92 },
  { symbol: "TSLA", name: "Tesla, Inc.", hype: 91, evidence: 48, sector: "Automotive / EV", change: -3.22, price: 356.09 },
  { symbol: "INTC", name: "Intel Corporation", hype: 58, evidence: 65, sector: "Semiconductors", change: -0.60, price: 88.97 },
];

export const NEWS_ARTICLES = [
  {
    id: 1, ticker: "NVDA",
    headline: "NVIDIA Announces Blackwell B200 GPU Mass Production Scale-Up Ahead of Schedule",
    source: "Reuters", time: "2h ago",
    hype: 78, evidence: 82,
    summary: "NVIDIA confirmed Blackwell GPU production ramp at TSMC is exceeding initial targets, with data center customers citing 6–8 week lead time improvements.",
    claims: ["Production 18% ahead of schedule", "TSMC yield rates improved to 94%", "Enterprise backlog exceeds $40B"],
    evidenceLinks: ["Q1 2024 10-Q Filing", "TSMC Supply Chain Report"],
    flagged: false,
  },
  {
    id: 2, ticker: "NVDA",
    headline: "Analysts Predict NVDA Will Reach $1,200 on 'Insatiable' AI Demand",
    source: "Seeking Alpha", time: "5h ago",
    hype: 91, evidence: 34,
    summary: "Multiple sell-side analysts raised price targets citing AI compute infrastructure expansion, though many projections lack specific customer commitment data.",
    claims: ["$1,200 PT within 12 months", "AI capex doubling in 2025", "No competitor for 3 years"],
    evidenceLinks: [],
    flagged: false,
  },
  {
    id: 3, ticker: "NVDA",
    headline: "SEC 10-K Filing: NVIDIA Discloses $18.4B Data Center Revenue, 427% YoY Growth",
    source: "SEC EDGAR", time: "1d ago",
    hype: 42, evidence: 97,
    summary: "Official SEC filing confirms record data center segment performance with detailed revenue breakdowns by geography and product line.",
    claims: ["$18.4B data center revenue", "427% YoY growth", "Gross margin 78.4%"],
    evidenceLinks: ["10-K Annual Report CY2024", "XBRL Financial Data"],
    flagged: false,
  },
  {
    id: 4, ticker: "NVDA",
    headline: "r/wallstreetbets: NVDA to $2000 — AI is bigger than the Internet",
    source: "Reddit WSB", time: "3h ago",
    hype: 97, evidence: 8,
    summary: "High-engagement WSB thread with 4.2K upvotes comparing NVIDIA's position to early Microsoft, citing speculative projections without financial disclosures.",
    claims: ["$2000 price target", "Bigger than internet revolution", "Buy now or regret forever"],
    evidenceLinks: [],
    flagged: false,
  },
];

export const TIMELINE_EVENTS = [
  { date: "Jun 18, 2024", type: "filing", title: "10-Q Filed with SEC", description: "Quarterly filing confirms $26B revenue guidance raised by 12%.", score_delta: +8, hype: 45, evidence: 94 },
  { date: "Jun 15, 2024", type: "narrative", title: "Narrative Shift: Demand Concerns Resurface", description: "Multiple analyst notes cite potential hyperscaler capex pullback. Community sentiment shifted -14 points.", score_delta: -14, hype: 72, evidence: 60 },
  { date: "Jun 10, 2024", type: "news", title: "Product Launch: Blackwell B200 GA Confirmed", description: "Official press release from NVIDIA Investor Relations confirms general availability timeline.", score_delta: +12, hype: 65, evidence: 88 },
  { date: "May 28, 2024", type: "social", title: "Reddit Surge: +340% Post Volume", description: "WSB and r/stocks saw explosive discussion around NVDA options activity.", score_delta: +19, hype: 89, evidence: 41 },
  { date: "May 28, 2024", type: "earnings", title: "Q1 FY2025 Earnings Beat", description: "EPS of $6.12 vs $5.65 expected. Revenue $26.04B vs $24.6B estimate.", score_delta: +22, hype: 61, evidence: 96 },
  { date: "May 15, 2024", type: "news", title: "Microsoft Azure Partnership Expanded", description: "MSFT confirms multi-year GPU cluster commitment — undisclosed dollar value.", score_delta: +6, hype: 70, evidence: 62 },
  { date: "May 8, 2024", type: "social", title: "Hype Spike: AMD Competition Dismissed", description: "Community posts claim AMD MI300X is 'irrelevant' — limited technical evidence cited.", score_delta: +11, hype: 88, evidence: 29 },
  { date: "Apr 30, 2024", type: "filing", title: "8-K Filed: Executive Compensation Update", description: "CEO Jensen Huang RSU grant disclosed. No material business updates.", score_delta: 0, hype: 40, evidence: 85 },
];

export const MAPPING_QUEUE = [
  { id: "m1", article: "Tesla Releases FSD v13 Beta to 400K Users", mapped: "RIVN", suggested: "TSLA", source: "TechCrunch", confidence: 0.42, reporter: "user", time: "1h ago", type: "Wrong Ticker" },
  { id: "m2", article: "NVIDIA Supplier TSMC Sees Record Orders", mapped: "TSM", suggested: "NVDA", source: "Bloomberg", confidence: 0.61, reporter: "auto", time: "3h ago", type: "Ambiguous" },
  { id: "m3", article: "Palantir Wins $250M DoD Contract for AIP Platform", mapped: "PLTR", suggested: "PLTR", source: "Reuters", confidence: 0.88, reporter: "user", time: "6h ago", type: "Verify" },
  { id: "m4", article: "Apple Vision Pro Sales Miss Analyst Estimates", mapped: "META", suggested: "AAPL", source: "WSJ", confidence: 0.29, reporter: "auto", time: "2d ago", type: "Wrong Ticker" },
  { id: "m5", article: "AMD MI300X Outperforms H100 on LLM Inference Benchmarks", mapped: "AMD", suggested: "AMD", source: "AnandTech", confidence: 0.91, reporter: "auto", time: "3d ago", type: "Verify" },
];

export const CHAT_HISTORY = [
  {
    role: "user",
    text: "Compare the evidence behind autonomous driving claims from Tesla vs Waymo",
    time: "10:42 AM",
  },
  {
    role: "ai",
    text: `**Multi-ticker analysis complete.** I searched across news, SEC filings, and community data for both **TSLA** and **Waymo (GOOGL)**.\n\n**Tesla FSD:**\n- Hype Score: 88/100 | Evidence Score: 52/100\n- Key claims in media: "Full autonomy by Q4 2024" — *No SEC filing corroboration found*\n- NHTSA open investigations: 4 active\n- Community sentiment: Highly polarized, 62% bullish\n\n**Waymo:**\n- Hype Score: 64/100 | Evidence Score: 79/100\n- Key claims: "6M+ robotaxi miles logged" — *Corroborated by Google Q1 2024 10-Q disclosure*\n- Regulatory approvals: California, Arizona commercial ops confirmed\n\n**Verdict:** Waymo carries significantly stronger evidence support for its autonomy claims. Tesla's claims outpace disclosed technical milestones by a wide margin.`,
    time: "10:42 AM",
    sources: ["TSLA 10-K 2023", "GOOGL Q1 2024 10-Q", "NHTSA Database", "r/RealTesla analysis"],
  },
  {
    role: "user",
    text: "What specific XBRL financial metrics does Tesla disclose for FSD revenue?",
    time: "10:44 AM",
  },
  {
    role: "ai",
    text: `**SEC Filing Analysis for TSLA — FSD Revenue Disclosure:**\n\nTesla classifies FSD revenue under **Automotive regulatory credits and deferred revenue** (ASC 606). Key XBRL metrics found:\n\n- Deferred revenue (FSD-related): $1.2B as of Q4 2023\n- Revenue recognized from FSD subscriptions: $326M (FY2023)\n- Subscription ARPU: ~$199/month (undisclosed in filing, derived)\n\n**Caution:** Tesla does not break out FSD separately in all filings. The $326M figure is extracted from narrative disclosure in Note 2, not a tagged XBRL element — making automated extraction unreliable.\n\n*Sources: TSLA 10-K FY2023 (Filed Feb 26, 2024), SEC EDGAR XBRL viewer*`,
    time: "10:44 AM",
    sources: ["TSLA 10-K FY2023", "SEC XBRL Data"],
  },
];

export const ALERTS_DATA = [
  { id: "a1", ticker: "NVDA", type: "narrative_shift", message: "Hype/Evidence score delta exceeded +10 threshold", time: "2h ago", read: false, severity: "high" },
  { id: "a2", ticker: "TSLA", type: "filing", message: "New SEC 8-K filing detected — executive compensation update", time: "5h ago", read: false, severity: "medium" },
  { id: "a3", ticker: "AMD", type: "narrative_shift", message: "Community sentiment reversed — net negative shift detected", time: "1d ago", read: true, severity: "medium" },
  { id: "a4", ticker: "PLTR", type: "hype_spike", message: "Reddit post volume +280% in 4 hours — hype score elevated", time: "2d ago", read: true, severity: "low" },
  { id: "a5", ticker: "NVDA", type: "filing", message: "Q1 FY2025 10-Q filed with SEC EDGAR", time: "3d ago", read: true, severity: "medium" },
];

export const MOCK_DATA = {
  TICKERS,
  NEWS_ARTICLES,
  TIMELINE_EVENTS,
  MAPPING_QUEUE,
  CHAT_HISTORY,
  ALERTS_DATA,
};