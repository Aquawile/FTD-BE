import { ReactNode } from "react";
import { Page } from "../../app/types";
import { Badge, Card, cn, getHypeColor, getEvidenceColor } from "../ui";
import { ChevronLeft, MessageSquare, ThumbsUp } from "lucide-react";

function CommunityPage({ navigate, ticker }: { navigate: (p: Page) => void; ticker: string }) {
  const posts = [
    { id: 1, subreddit: "r/wallstreetbets", author: "u/AIBullThesis", title: "NVDA is the new railroads — you either own the picks or you are left behind", score: 4280, comments: 312, hype: 97, evidence: 8, time: "3h ago", flair: "DD" },
    { id: 2, subreddit: "r/stocks", author: "u/DataDrivenFin", title: "Deep dive: Analyzing NVDA's actual Blackwell production claims vs. TSMC capacity data", score: 892, comments: 76, hype: 42, evidence: 78, time: "5h ago", flair: "Analysis" },
    { id: 3, subreddit: "r/investing", author: "u/ValueSeeker99", title: "NVDA P/E at 73x — when does price disconnect from fundamentals?", score: 1540, comments: 203, hype: 55, evidence: 67, time: "8h ago", flair: "Discussion" },
    { id: 4, subreddit: "r/wallstreetbets", author: "u/NVDAGang", title: "NVDA $2000 EOY confirmed by my AI prediction model 🚀🚀🚀", score: 6700, comments: 445, hype: 99, evidence: 4, time: "12h ago", flair: "Meme" },
    { id: 5, subreddit: "r/stocks", author: "u/TechResearchPro", title: "Breaking down NVDA's China export risk — what the SEC filings actually say", score: 423, comments: 51, hype: 35, evidence: 89, time: "1d ago", flair: "News" },
  ];
  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("ticker")} className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground cursor-pointer"><ChevronLeft size={14} /> {ticker}</button>
        <h1 className="text-xl font-bold flex-1">Community Sentiment — {ticker}</h1>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-6">
        {[
          { label: "Total Posts (7d)", value: "8,431", color: "#3B82F6" },
          { label: "Avg Hype Score", value: "79/100", color: "#F59E0B" },
          { label: "Avg Evidence Score", value: "18/100", color: "#10B981" },
          { label: "Net Sentiment", value: "+62%", color: "#8B5CF6" },
        ].map(s => (
          <Card key={s.label} className="p-4 text-center">
            <div className="font-mono font-bold text-xl mb-1" style={{ color: s.color }}>{s.value}</div>
            <div className="text-xs text-muted-foreground">{s.label}</div>
          </Card>
        ))}
      </div>
      <div className="space-y-3">
        {posts.map(p => (
          <Card key={p.id} className="p-4">
            <div className="flex items-start gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <Badge variant="neutral" className="text-xs">{p.subreddit}</Badge>
                  <Badge variant={p.flair === "DD" || p.flair === "Analysis" ? "default" : p.flair === "Meme" ? "danger" : "neutral"} className="text-xs">{p.flair}</Badge>
                  <span className="text-xs text-muted-foreground">{p.author}</span>
                  <span className="text-xs text-muted-foreground">{p.time}</span>
                </div>
                <h4 className="font-medium text-sm text-foreground mb-2 leading-snug">{p.title}</h4>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1"><ThumbsUp size={10} /> {p.score.toLocaleString()}</span>
                  <span className="flex items-center gap-1"><MessageSquare size={10} /> {p.comments}</span>
                </div>
              </div>
              <div className="flex flex-col items-end gap-1 shrink-0">
                <div className="text-xs font-mono" style={{ color: getHypeColor(p.hype) }}>H:{p.hype}</div>
                <div className="text-xs font-mono" style={{ color: getEvidenceColor(p.evidence) }}>E:{p.evidence}</div>
                <div className={cn("text-xs font-semibold mt-1", p.evidence < 20 ? "text-red-400" : p.evidence > 60 ? "text-emerald-400" : "text-yellow-400")}>
                  {p.evidence < 20 ? "Low Signal" : p.evidence > 60 ? "High Signal" : "Med Signal"}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 13: Ticker Comparison
// ────────────────────────────────────────────────

export default CommunityPage;
