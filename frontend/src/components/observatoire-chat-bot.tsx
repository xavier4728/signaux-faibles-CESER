"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { MessageCircle, X, Send, Loader2, Sparkles, Maximize2, Minimize2 } from "lucide-react";

const mdComponents: Components = {
  table: ({ children, ...props }) => (
    <div className="my-2 overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-xs" {...props}>{children}</table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-[var(--color-ceser-blue)]/5 text-left" {...props}>{children}</thead>
  ),
  th: ({ children, ...props }) => (
    <th className="whitespace-nowrap px-2.5 py-1.5 text-xs font-semibold text-foreground" {...props}>{children}</th>
  ),
  td: ({ children, ...props }) => (
    <td className="border-t border-border/50 px-2.5 py-1.5 text-xs text-muted-foreground" {...props}>{children}</td>
  ),
  ul: ({ children, ...props }) => (
    <ul className="my-1 ml-4 list-disc space-y-0.5" {...props}>{children}</ul>
  ),
  ol: ({ children, ...props }) => (
    <ol className="my-1 ml-4 list-decimal space-y-0.5" {...props}>{children}</ol>
  ),
  li: ({ children, ...props }) => (
    <li className="text-sm leading-relaxed" {...props}>{children}</li>
  ),
  p: ({ children, ...props }) => (
    <p className="my-1 text-sm leading-relaxed" {...props}>{children}</p>
  ),
  strong: ({ children, ...props }) => (
    <strong className="font-semibold text-foreground" {...props}>{children}</strong>
  ),
  h1: ({ children, ...props }) => (
    <h1 className="mb-1 mt-2 text-sm font-bold text-foreground" {...props}>{children}</h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 className="mb-1 mt-2 text-sm font-bold text-foreground" {...props}>{children}</h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 className="mb-0.5 mt-1.5 text-sm font-semibold text-foreground" {...props}>{children}</h3>
  ),
};

interface Message {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTED_QUESTIONS = [
  "Quel est le taux de conversion global ?",
  "Quelles régions ont le plus de préconisations ?",
  "Quelles thématiques dominent par région ?",
  "Comment se recoupent les régions ?",
];

export function ObservatoireChatBot() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    if (open && inputRef.current) {
      inputRef.current.focus();
    }
  }, [open]);

  const sendMessage = useCallback(async (overrideText?: string) => {
    const text = overrideText ?? input;
    if (!text.trim() || loading) return;

    const userMsg: Message = { role: "user", content: text.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${apiUrl}/api/dashboard/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.content,
          history: messages.map((m) => ({ role: m.role, content: m.content })),
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erreur serveur" }));
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `Erreur : ${err.detail || "Impossible de contacter le serveur."}` },
        ]);
        return;
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Erreur de connexion au serveur." },
      ]);
    } finally {
      setLoading(false);
    }
  }, [input, loading, messages, apiUrl]);

  return (
    <>
      {/* Floating button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-[var(--color-ceser-blue)] px-4 py-3 text-sm font-medium text-white shadow-lg transition-all hover:bg-[var(--color-ceser-blue-light)] hover:shadow-xl active:scale-95"
        >
          <MessageCircle className="h-5 w-5" />
          <span>Besoin d&apos;aide ?</span>
        </button>
      )}

      {/* Chat window */}
      {open && (
        <div
          className={`fixed z-50 flex flex-col overflow-hidden border border-border bg-white shadow-2xl transition-all duration-300 ease-in-out ${
            expanded
              ? "bottom-0 right-0 h-[75vh] w-[75vw] rounded-tl-2xl"
              : "bottom-6 right-6 h-[580px] w-[420px] rounded-2xl"
          }`}
        >
          {/* Header */}
          <div className="flex items-center justify-between bg-[var(--color-ceser-blue)] px-4 py-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Assistant CESER</p>
                <p className="text-[10px] text-white/70">Observatoire</p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setExpanded(!expanded)}
                className="h-7 w-7 text-white/80 hover:bg-white/10 hover:text-white"
                title={expanded ? "Réduire" : "Agrandir"}
              >
                {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => { setOpen(false); setExpanded(false); }}
                className="h-7 w-7 text-white/80 hover:bg-white/10 hover:text-white"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="flex h-full flex-col items-center justify-center text-center">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-ceser-blue-pale)]">
                  <MessageCircle className="h-6 w-6 text-[var(--color-ceser-blue)]" />
                </div>
                <p className="text-sm font-medium text-foreground">
                  Comment puis-je vous aider ?
                </p>
                <p className="mt-1 max-w-[260px] text-xs text-muted-foreground">
                  Posez-moi une question sur les données de l&apos;Observatoire : KPIs, régions, thématiques, recoupements...
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-1.5">
                  {SUGGESTED_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-[var(--color-ceser-blue)] hover:text-[var(--color-ceser-blue)]"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) =>
              msg.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl rounded-br-md bg-[var(--color-ceser-blue)] px-3.5 py-2.5 text-sm leading-relaxed text-white">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div key={i} className="rounded-2xl rounded-bl-md bg-[var(--color-ceser-blue-pale)] px-3.5 py-2.5">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              ),
            )}

            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-md bg-[var(--color-ceser-blue-pale)] px-3.5 py-2.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-[var(--color-ceser-blue)]" />
                  <span className="text-xs text-muted-foreground">Réflexion...</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-border bg-white px-3 py-2.5">
            <div className="flex items-center gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Écrivez votre message ici..."
                className="flex-1 rounded-full border border-border bg-muted/50 px-3.5 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground/60 focus:border-[var(--color-ceser-blue)] focus:ring-1 focus:ring-[var(--color-ceser-blue)]/20"
                disabled={loading}
              />
              <Button
                size="icon"
                onClick={sendMessage}
                disabled={!input.trim() || loading}
                className="h-9 w-9 shrink-0 rounded-full bg-[var(--color-ceser-blue)] hover:bg-[var(--color-ceser-blue-light)] disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
