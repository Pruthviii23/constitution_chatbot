"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

// ── Types ────────────────────────────────────────────────────────
interface Message {
  role: "user" | "bot";
  content: string;
  sources?: number[];
}

// ── Main component ───────────────────────────────────────────────
export default function Home() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [sessionId, setSessionId]   = useState<string | null>(null);
  const bottomRef                   = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const question = input.trim();
    if (!question || loading) return;

    // Optimistically add user message
    setMessages(prev => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, session_id: sessionId }),
        }
      );

      if (!res.ok) throw new Error(`API error: ${res.status}`);
      const data = await res.json();

      // Save session_id from first response
      if (!sessionId) setSessionId(data.session_id);

      setMessages(prev => [
        ...prev,
        { role: "bot", content: data.answer, sources: data.sources },
      ]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        { role: "bot", content: "⚠️ Something went wrong. Is the backend running?" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const startNewChat = async () => {
    if (sessionId) {
      await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/session/${sessionId}`,
        { method: "DELETE" }
      );
    }
    setSessionId(null);
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏛️</span>
          <div>
            <h1 className="font-bold text-lg leading-tight">Constitution of India</h1>
            <p className="text-xs text-gray-400">Ask anything about the Indian Constitution</p>
          </div>
        </div>
        <button
          onClick={startNewChat}
          className="text-sm px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 transition text-gray-300"
        >
          + New Chat
        </button>
      </header>

      {/* ── Messages ── */}
      <main className="flex-1 overflow-y-auto px-4 py-6 space-y-6 max-w-3xl w-full mx-auto">

        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-4 text-gray-500">
            <span className="text-5xl">🇮🇳</span>
            <p className="text-lg font-medium text-gray-400">
              Ask me anything about the Indian Constitution
            </p>
            <div className="grid grid-cols-1 gap-2 w-full max-w-md mt-2">
              {[
                "What are the Fundamental Rights?",
                "Explain the Directive Principles of State Policy.",
                "What is the procedure to amend the Constitution?",
                "What powers does the President have?",
              ].map(q => (
                <button
                  key={q}
                  onClick={() => { setInput(q); }}
                  className="text-sm text-left px-4 py-2.5 rounded-xl border border-gray-700 hover:border-orange-500 hover:text-orange-400 transition"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>

            {msg.role === "bot" && (
              <div className="w-8 h-8 rounded-full bg-orange-600 flex items-center justify-center text-sm flex-shrink-0 mt-1">
                🏛️
              </div>
            )}

            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed
              ${msg.role === "user"
                ? "bg-orange-600 text-white rounded-br-sm"
                : "bg-gray-800 text-gray-100 rounded-bl-sm"
              }`}
            >
              {msg.role === "bot" ? (
                <>
                  <ReactMarkdown
                    components={{
                      ul: ({node, ...props}) => <ul className="list-disc ml-4 space-y-1 mt-1" {...props} />,
                      ol: ({node, ...props}) => <ol className="list-decimal ml-4 space-y-1 mt-1" {...props} />,
                      li: ({node, ...props}) => <li className="leading-relaxed" {...props} />,
                      strong: ({node, ...props}) => <strong className="text-orange-300" {...props} />,
                      p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                  {msg.sources && msg.sources.length > 0 && (
                    <p className="mt-2 text-xs text-gray-500">
                      📄 Sources: pages {msg.sources.join(", ")}
                    </p>
                  )}
                </>
              ) : (
                msg.content
              )}
            </div>

            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-sm flex-shrink-0 mt-1">
                👤
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="w-8 h-8 rounded-full bg-orange-600 flex items-center justify-center text-sm flex-shrink-0">
              🏛️
            </div>
            <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3">
              <div className="flex gap-1 items-center h-5">
                <span className="w-2 h-2 bg-orange-400 rounded-full animate-bounce [animation-delay:0ms]"/>
                <span className="w-2 h-2 bg-orange-400 rounded-full animate-bounce [animation-delay:150ms]"/>
                <span className="w-2 h-2 bg-orange-400 rounded-full animate-bounce [animation-delay:300ms]"/>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ── Input bar ── */}
      <div className="border-t border-gray-800 bg-gray-900 px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the Indian Constitution..."
            rows={1}
            className="flex-1 resize-none bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-sm
                       focus:outline-none focus:border-orange-500 placeholder-gray-500 leading-relaxed"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-3 rounded-xl bg-orange-600 hover:bg-orange-500 disabled:opacity-40
                       disabled:cursor-not-allowed transition font-medium text-sm"
          >
            Send
          </button>
        </div>
        <p className="text-center text-xs text-gray-600 mt-2">
          Answers are based solely on the Constitution of India PDF · Press Enter to send
        </p>
      </div>

    </div>
  );
}