"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

interface Message {
  role: "user" | "bot";
  content: string;
  sources?: number[];
  time?: string;
}

const POPULAR_ARTICLES = [
  { num: "Article 14", desc: "Equality before law" },
  { num: "Article 19", desc: "Freedom of speech and expression" },
  { num: "Article 21", desc: "Protection of life and personal liberty" },
  { num: "Article 32", desc: "Right to constitutional remedies" },
  { num: "Article 368", desc: "Amendment of the Constitution" },
];

const AMENDMENTS = [
  { title: "105th Amendment Act, 2021", desc: "Cooperative societies" },
  { title: "103rd Amendment Act, 2019", desc: "Economically Weaker Sections" },
  { title: "100th Amendment Act, 2015", desc: "Goods and Services Tax (GST)" },
];

const SUGGESTED = [
  "What are the Fundamental Rights?",
  "Explain Directive Principles of State Policy.",
  "What is the procedure to amend the Constitution?",
  "What powers does the President have?",
];

const AMBEDKAR_QUOTE =
  '"The Constitution is not merely a lawyers\' document, it is a vehicle of Life, and its spirit is always the Spirit of Age."';

function getTime() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async (question?: string) => {
    const q = (question ?? input).trim();
    if (!q || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: q, time: getTime() }]);
    setInput("");
    setSuggestions([]);
    setLoading(true);

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, session_id: sessionId }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (!sessionId) setSessionId(data.session_id);

      setMessages((prev) => [
        ...prev,
        { role: "bot", content: data.answer, sources: data.sources, time: getTime() },
      ]);

      // Generate follow-up suggestions based on the question
      const followUps = generateFollowUps(q);
      setSuggestions(followUps);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "bot", content: "⚠️ Something went wrong. Please try again.", time: getTime() },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const generateFollowUps = (q: string): string[] => {
    if (q.toLowerCase().includes("article 21"))
      return ["What is personal liberty?", "Related landmark cases", "Is right to privacy under Article 21?"];
    if (q.toLowerCase().includes("fundamental"))
      return ["Which article covers right to equality?", "Can rights be suspended?", "What are Directive Principles?"];
    if (q.toLowerCase().includes("president"))
      return ["What is President's Rule?", "Who elects the President?", "Presidential vs Parliamentary system"];
    return ["Tell me more", "Related articles", "Historical context"];
  };

  const startNewChat = async () => {
    if (sessionId) {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL}/session/${sessionId}`, { method: "DELETE" });
    }
    setSessionId(null);
    setMessages([]);
    setSuggestions([]);
  };

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'Inter', sans-serif", background: "#0f1923" }}>

      {/* ── Left Sidebar ── */}
      <aside style={{
        width: 200, minWidth: 200, background: "#0d1f35", display: "flex",
        flexDirection: "column", padding: "24px 16px", gap: 8, borderRight: "1px solid #1a2f47"
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <div style={{
            width: 40, height: 40, borderRadius: 10, background: "linear-gradient(135deg,#c9a84c,#8b6914)",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0
          }}>⚖️</div>
          <div>
            <div style={{ color: "#e8d5a3", fontWeight: 700, fontSize: 15, lineHeight: 1.2 }}>ConstiBot</div>
            <div style={{ color: "#5a7a99", fontSize: 10, lineHeight: 1.4 }}>Your Guide to the<br />Indian Constitution</div>
          </div>
        </div>

        {/* New Chat */}
        <button onClick={startNewChat} style={{
          background: "#1a3a5c", border: "1px solid #2a5a8c", color: "#e8d5a3",
          borderRadius: 8, padding: "10px 14px", cursor: "pointer", fontSize: 13,
          fontWeight: 600, display: "flex", alignItems: "center", gap: 8, marginBottom: 8
        }}>
          <span style={{ fontSize: 16 }}>+</span> New Chat
        </button>

        {/* Nav */}
        <button style={{
          background: "#132b44", border: "none", color: "#8ab0cc",
          borderRadius: 8, padding: "10px 14px", cursor: "pointer", fontSize: 13,
          fontWeight: 500, display: "flex", alignItems: "center", gap: 8, textAlign: "left"
        }}>
          🏠 Home
        </button>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Quote */}
        <div style={{
          background: "#0a1824", borderRadius: 10, padding: "14px 12px",
          borderLeft: "3px solid #c9a84c"
        }}>
          <div style={{ fontSize: 16, textAlign: "center", marginBottom: 6 }}>⚖️</div>
          <p style={{ color: "#8ab0cc", fontSize: 10.5, lineHeight: 1.6, fontStyle: "italic", margin: 0 }}>
            {AMBEDKAR_QUOTE}
          </p>
          <p style={{ color: "#c9a84c", fontSize: 10, marginTop: 8, margin: "8px 0 0", fontWeight: 600 }}>
            — B. R. Ambedkar
          </p>
        </div>
      </aside>

      {/* ── Main Chat Area ── */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>

        {/* Hero banner */}
        <div style={{
          background: "linear-gradient(135deg, #f5f0e8 0%, #ede4d0 100%)",
          padding: "28px 40px", position: "relative", overflow: "hidden",
          borderBottom: "1px solid #d4c4a0"
        }}>
          <div style={{ position: "absolute", right: 40, top: "50%", transform: "translateY(-50%)", opacity: 0.15, fontSize: 80 }}>
            🏛️
          </div>
          <div style={{ position: "relative" }}>
            <h1 style={{
              margin: 0, fontSize: 22, fontWeight: 700,
              color: "#1a2f47", letterSpacing: "-0.3px"
            }}>
              Ask anything about the Indian Constitution
            </h1>
            <p style={{ margin: "6px 0 0", color: "#6b7c8d", fontSize: 13 }}>
              Accurate. Reliable. Constitutionally rooted.
            </p>
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: "auto", padding: "28px 40px",
          background: "#f7f3ed", display: "flex", flexDirection: "column", gap: 20
        }}>

          {messages.length === 0 && !loading && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: 16 }}>
              <div style={{ fontSize: 48 }}>🇮🇳</div>
              <p style={{ color: "#8a9aaa", fontSize: 15, margin: 0 }}>
                Select a topic below or type your question
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 560 }}>
                {SUGGESTED.map((s) => (
                  <button key={s} onClick={() => sendMessage(s)} style={{
                    background: "#fff", border: "1px solid #d4c4a0", borderRadius: 20,
                    padding: "8px 16px", fontSize: 13, color: "#2a4a6a", cursor: "pointer",
                    fontWeight: 500
                  }}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{
              display: "flex", flexDirection: msg.role === "user" ? "row-reverse" : "row",
              gap: 12, alignItems: "flex-start"
            }}>
              {/* Avatar */}
              <div style={{
                width: 36, height: 36, borderRadius: "50%", flexShrink: 0,
                background: msg.role === "user" ? "#1a3a5c" : "linear-gradient(135deg,#c9a84c,#8b6914)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 16, marginTop: 2
              }}>
                {msg.role === "user" ? "👤" : "🏛️"}
              </div>

              <div style={{ maxWidth: "72%", display: "flex", flexDirection: "column", gap: 4 }}>
                {/* Bubble */}
                <div style={{
                  background: msg.role === "user" ? "#1a3a5c" : "#fff",
                  color: msg.role === "user" ? "#e8d5a3" : "#1a2f47",
                  borderRadius: msg.role === "user" ? "18px 4px 18px 18px" : "4px 18px 18px 18px",
                  padding: "14px 18px", fontSize: 14, lineHeight: 1.7,
                  boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                  border: msg.role === "bot" ? "1px solid #e8dfc8" : "none"
                }}>
                  {msg.role === "bot" ? (
                    <>
                      <ReactMarkdown components={{
                        ul: ({ ...p }) => <ul style={{ paddingLeft: 20, margin: "6px 0" }} {...p} />,
                        ol: ({ ...p }) => <ol style={{ paddingLeft: 20, margin: "6px 0" }} {...p} />,
                        li: ({ ...p }) => <li style={{ marginBottom: 4 }} {...p} />,
                        p: ({ ...p }) => <p style={{ margin: "0 0 8px" }} {...p} />,
                        blockquote: ({ ...p }) => (
                          <blockquote style={{
                            borderLeft: "3px solid #c9a84c", paddingLeft: 14,
                            margin: "10px 0", color: "#3a5a7a", fontStyle: "italic"
                          }} {...p} />
                        ),
                      }}>
                        {msg.content}
                      </ReactMarkdown>

                      {/* Source card */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div style={{ fontSize: 11, color: "#8a9aaa", fontWeight: 600, marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.5px" }}>
                            Source
                          </div>
                          <div style={{
                            display: "inline-flex", alignItems: "center", gap: 8,
                            background: "#f5f0e8", border: "1px solid #d4c4a0",
                            borderRadius: 8, padding: "6px 12px", fontSize: 12, color: "#2a4a6a"
                          }}>
                            📄 Constitution of India · Pages {msg.sources.join(", ")}
                            <span style={{ color: "#c9a84c" }}>↗</span>
                          </div>
                        </div>
                      )}

                      {/* Action row */}
                      <div style={{ display: "flex", gap: 12, marginTop: 10 }}>
                        {["🔖", "📋", "👍", "👎"].map((icon) => (
                          <button key={icon} style={{
                            background: "none", border: "none", cursor: "pointer",
                            fontSize: 14, opacity: 0.5, padding: 0
                          }}>{icon}</button>
                        ))}
                        <span style={{ marginLeft: "auto", fontSize: 11, color: "#aab0bb" }}>{msg.time}</span>
                      </div>
                    </>
                  ) : (
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 12 }}>
                      <span>{msg.content}</span>
                      <span style={{ fontSize: 11, opacity: 0.7, whiteSpace: "nowrap" }}>{msg.time} ✓✓</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div style={{
                width: 36, height: 36, borderRadius: "50%",
                background: "linear-gradient(135deg,#c9a84c,#8b6914)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16
              }}>🏛️</div>
              <div style={{
                background: "#fff", borderRadius: "4px 18px 18px 18px",
                padding: "14px 18px", border: "1px solid #e8dfc8",
                boxShadow: "0 1px 4px rgba(0,0,0,0.08)"
              }}>
                <div style={{ display: "flex", gap: 5, alignItems: "center" }}>
                  {[0, 1, 2].map((i) => (
                    <div key={i} style={{
                      width: 8, height: 8, borderRadius: "50%", background: "#c9a84c",
                      animation: "bounce 1.2s infinite",
                      animationDelay: `${i * 0.2}s`
                    }} />
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Follow-up suggestions */}
          {suggestions.length > 0 && !loading && (
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingLeft: 48 }}>
              {suggestions.map((s) => (
                <button key={s} onClick={() => sendMessage(s)} style={{
                  background: "#fff", border: "1px solid #d4c4a0", borderRadius: 20,
                  padding: "7px 14px", fontSize: 12, color: "#2a4a6a",
                  cursor: "pointer", fontWeight: 500
                }}>{s}</button>
              ))}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div style={{
          background: "#f0ebe0", borderTop: "1px solid #d4c4a0", padding: "16px 40px"
        }}>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end" }}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Ask a question about any Article, Amendment, Case..."
              rows={1}
              style={{
                flex: 1, resize: "none", background: "#fff",
                border: "1px solid #d4c4a0", borderRadius: 12,
                padding: "12px 16px", fontSize: 14, color: "#1a2f47",
                outline: "none", lineHeight: 1.5, fontFamily: "inherit"
              }}
            />
            <div style={{ fontSize: 11, color: "#aab0bb", whiteSpace: "nowrap", paddingBottom: 14 }}>
              {input.length}/1000
            </div>
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              style={{
                width: 44, height: 44, borderRadius: "50%",
                background: loading || !input.trim() ? "#c4b99a" : "linear-gradient(135deg,#1a3a5c,#0d2438)",
                border: "none", cursor: loading || !input.trim() ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18, flexShrink: 0
              }}
            >
              ➤
            </button>
          </div>
        </div>
      </main>

      {/* ── Right Sidebar ── */}
      <aside style={{
        width: 220, minWidth: 220, background: "#fff",
        borderLeft: "1px solid #e8dfc8", padding: "24px 16px",
        overflowY: "auto", display: "flex", flexDirection: "column", gap: 24
      }}>
        {/* Constitution Explorer */}
        <div>
          <h3 style={{ margin: "0 0 6px", fontSize: 13, color: "#1a2f47", fontWeight: 700 }}>
            Constitution Explorer
          </h3>
          <p style={{ margin: "0 0 12px", fontSize: 11, color: "#8a9aaa", lineHeight: 1.5 }}>
            Explore Parts, Schedules, Articles and more.
          </p>
          <div style={{
            background: "#f5f0e8", borderRadius: 10, padding: 12,
            display: "flex", justifyContent: "space-between", alignItems: "center",
            border: "1px solid #e8dfc8"
          }}>
            <button style={{
              background: "#1a3a5c", color: "#e8d5a3", border: "none",
              borderRadius: 7, padding: "8px 12px", fontSize: 12,
              fontWeight: 600, cursor: "pointer"
            }}>Explore Now</button>
            <div style={{ fontSize: 32 }}>📜</div>
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: "#e8dfc8" }} />

        {/* Popular Articles */}
        <div>
          <h3 style={{ margin: "0 0 12px", fontSize: 13, color: "#1a2f47", fontWeight: 700 }}>
            Popular Articles
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {POPULAR_ARTICLES.map((a) => (
              <button key={a.num} onClick={() => sendMessage(`Explain ${a.num} of the Indian Constitution`)}
                style={{
                  background: "none", border: "none", padding: 0,
                  textAlign: "left", cursor: "pointer"
                }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1a5276" }}>{a.num}</div>
                <div style={{ fontSize: 11, color: "#8a9aaa" }}>{a.desc}</div>
              </button>
            ))}
          </div>
          <button style={{
            background: "none", border: "none", color: "#c9a84c",
            fontSize: 12, fontWeight: 600, cursor: "pointer", padding: "8px 0 0",
          }}>View all Articles →</button>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: "#e8dfc8" }} />

        {/* Recent Amendments */}
        <div>
          <h3 style={{ margin: "0 0 12px", fontSize: 13, color: "#1a2f47", fontWeight: 700 }}>
            Recent Amendments
          </h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {AMENDMENTS.map((a) => (
              <button key={a.title} onClick={() => sendMessage(`Explain the ${a.title}`)}
                style={{ background: "none", border: "none", padding: 0, textAlign: "left", cursor: "pointer" }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1a5276" }}>{a.title}</div>
                <div style={{ fontSize: 11, color: "#8a9aaa" }}>{a.desc}</div>
              </button>
            ))}
          </div>
          <button style={{
            background: "none", border: "none", color: "#c9a84c",
            fontSize: 12, fontWeight: 600, cursor: "pointer", padding: "8px 0 0",
          }}>View all Amendments →</button>
        </div>
      </aside>

      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-6px); }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #d4c4a0; border-radius: 3px; }
        textarea:focus { border-color: #c9a84c !important; box-shadow: 0 0 0 3px rgba(201,168,76,0.15); }
      `}</style>
    </div>
  );
}
