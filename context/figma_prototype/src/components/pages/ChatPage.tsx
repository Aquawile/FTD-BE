import { useState, useEffect, useRef } from "react";
import { Page } from "../../app/types";
import { Badge, Btn, cn } from "../ui";
import { Radio, RefreshCw, Send, Sparkles, Zap } from "lucide-react";
import { TICKERS, NEWS_ARTICLES, TIMELINE_EVENTS, WORKSPACES, MAPPING_QUEUE, CHAT_HISTORY, ALERTS_DATA } from "../../mockData";

function ChatPage({ navigate }: { navigate: (p: Page) => void }) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(CHAT_HISTORY);
  const [loading, setLoading] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  const send = () => {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", text: input, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(m => [...m, userMsg]);
    setInput("");
    setLoading(true);
    setTimeout(() => {
      setMessages(m => [...m, { role: "ai", text: "**Analyzing your query...**\n\nI searched across SEC filings, financial news, and community data. Based on available evidence, the claims in your query are partially corroborated. Key SEC disclosures support the revenue figures, but community-driven price projections exceed verifiable guidance by a significant margin.\n\n*Always verify against primary sources before making research decisions.*", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), sources: ["SEC EDGAR", "Alpha Vantage News", "Reddit API"] }]);
      setLoading(false);
    }, 1500);
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b border-border">
        <div className="w-9 h-9 rounded-xl bg-purple-500/10 flex items-center justify-center">
          <Sparkles size={18} className="text-purple-400" />
        </div>
        <div>
          <h2 className="font-semibold">AI Research Assistant</h2>
          <div className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Radio size={9} className="text-emerald-400 animate-pulse" /> Live · Multi-hop RAG enabled · Sources always cited
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <Badge variant="purple"><Zap size={10} /> Gemini 1.5 Pro</Badge>
          <Btn variant="ghost" size="sm" icon={<Trash2 size={12} />}>Clear</Btn>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {/* Intro */}
        <div className="flex items-center justify-center">
          <div className="text-xs text-muted-foreground bg-secondary px-3 py-1.5 rounded-full">Today · Session started</div>
        </div>

        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-3", msg.role === "user" ? "flex-row-reverse" : "flex-row")}>
            {msg.role === "ai" ? (
              <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center shrink-0">
                <Sparkles size={14} className="text-purple-400" />
              </div>
            ) : (
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center shrink-0 text-white text-xs font-bold">IB</div>
            )}
            <div className={cn("max-w-[75%] space-y-2", msg.role === "user" ? "items-end" : "items-start")}>
              <div className={cn("px-4 py-3 rounded-2xl text-sm leading-relaxed", msg.role === "user" ? "bg-primary text-white rounded-tr-sm" : "bg-card border border-border text-foreground rounded-tl-sm")}>
                {msg.text.split("\n").map((line, j) => {
                  const formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\*(.*?)\*/g, '<em>$1</em>');
                  return <p key={j} className="whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatted || "&nbsp;" }} />;
                })}
              </div>
              {"sources" in msg && msg.sources && (
                <div className="flex flex-wrap gap-1.5 px-1">
                  {(msg.sources as string[]).map(s => <Badge key={s} variant="neutral" className="text-xs">{s}</Badge>)}
                </div>
              )}
              <div className="text-xs text-muted-foreground px-1">{msg.time}</div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-purple-500/10 flex items-center justify-center shrink-0">
              <Sparkles size={14} className="text-purple-400 animate-pulse" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm bg-card border border-border text-sm text-muted-foreground flex items-center gap-2">
              <RefreshCw size={12} className="animate-spin" /> Searching across SEC filings, news, and community data...
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {/* Suggested prompts */}
      {messages.length <= 2 && (
        <div className="px-6 pb-3 flex gap-2 flex-wrap">
          {["Compare NVDA vs AMD evidence scores", "What SEC filings support Tesla FSD claims?", "Summarize PLTR earnings narrative"].map(p => (
            <button key={p} className="px-3 py-1.5 bg-secondary border border-border rounded-lg text-xs text-muted-foreground hover:text-foreground hover:border-primary/30 cursor-pointer transition-all" onClick={() => setInput(p)}>{p}</button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-6 pb-6">
        <div className="flex gap-2 bg-input-background border border-border rounded-xl p-2 focus-within:border-primary/50 transition-all">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask a complex question about any ticker or topic..."
            rows={2}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none resize-none py-1 px-2"
          />
          <button onClick={send} disabled={!input.trim() || loading} className="self-end w-9 h-9 rounded-lg bg-primary text-white flex items-center justify-center hover:bg-primary/90 disabled:opacity-40 cursor-pointer transition-all">
            <Send size={15} />
          </button>
        </div>
        <div className="text-xs text-muted-foreground mt-2 text-center">Not investment advice · AI may make mistakes · Always verify primary sources</div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────
// PAGE 18: Alerts
// ────────────────────────────────────────────────

export default ChatPage;
