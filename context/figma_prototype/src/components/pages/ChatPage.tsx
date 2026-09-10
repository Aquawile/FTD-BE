// ────────────────────────────────────────────────
// CHAT PAGE
// ────────────────────────────────────────────────

import { useState, useEffect, useRef } from "react";
import { Card, Button as Btn, Send, MessageSquare, Loader2, Bot } from "./ui";
import { cn } from "../utils";

interface ChatPageProps {
  navigate: (p: string) => void;
}

export function ChatPage({ navigate }: ChatPageProps) {
  const [messages, setMessages] = useState<Array<{ role: "user" | "ai"; text: string; time: string }>>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = { role: "user" as const, text: input, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      // TODO: Connect to actual AI endpoint
      await new Promise(r => setTimeout(r, 1000));
      setMessages(prev => [...prev, { role: "ai", text: "AI response coming soon. This feature will be implemented in a later layer.", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }]);
    } catch {
      // Error handling
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">AI Research Assistant</h1>
        <p className="text-muted-foreground text-sm mt-1">Ask questions about tickers, filings, news, or market analysis</p>
      </div>

      <div className="flex-1 overflow-y-auto space-y-4 mb-6">
        {CHAT_HISTORY.map((m, i) => (
          <div key={i} className={cn("flex gap-3", m.role === "user" ? "justify-end" : "justify-start")}>
            <div className={cn("max-w-[70%] rounded-2xl px-4 py-3", m.role === "user" ? "bg-primary text-primary-foreground rounded-tr-none" : "bg-secondary rounded-tl-none")}>
              <div className="flex items-center gap-2 mb-1">
                {m.role === "ai" && <Bot size={14} className="text-muted-foreground" />}
                <span className="text-xs text-muted-foreground font-medium capitalize">{m.role}</span>
                <span className="text-xs text-muted-foreground/50">{m.time}</span>
              </div>
              <p className="text-sm whitespace-pre-wrap">{m.text}</p>
              {m.sources && (
                <div className="mt-2 text-xs text-muted-foreground">
                  Sources: {m.sources.join(", ")}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex gap-3">
            <Bot size={14} className="animate-spin text-muted-foreground" />
            <div className="bg-secondary rounded-xl px-4 py-3 w-64 animate-pulse"></div>
          </div>
        )}

        <div id="messages-end" ref={messagesEndRef} />
      </div>

      <div className="border-t border-border pt-4">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
              placeholder="Ask about tickers, filings, news, analysis..."
              className="w-full bg-input-background border border-border rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50 px-4 py-3"
              disabled={loading}
            />
            <Button onClick={sendMessage} disabled={!input.trim() || loading} icon={<Send size={16} />} size="sm" variant="primary">
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Send size={16} />}
            </Button>
          </div>
        </div>
      </div>
      <div id="messages-end" ref={messagesEndRef} />
    </div>
  );
}

export default ChatPage;