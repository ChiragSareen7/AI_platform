import { useState, useRef, useEffect } from "react";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatWindowRef = useRef(null);

  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: trimmed,
          session_id: "default",
        }),
      });

      if (!res.ok) {
        throw new Error(`Backend error: ${res.status}`);
      }

      const data = await res.json();
      const assistantMessage = {
        role: "assistant",
        content: data.response,
        sources: data.sources || [],
        latency: data.latency,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage = {
        role: "assistant",
        content:
          "Sorry, something went wrong when contacting the AI service. Please try again.",
      };
      setMessages((prev) => [...prev, errorMessage]);
      // eslint-disable-next-line no-console
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center">
      <style jsx global>{`
        body {
          margin: 0;
          font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
            sans-serif;
          background: radial-gradient(circle at top, #1e293b, #020617);
          color: #e5e7eb;
        }
      `}</style>
      <main className="w-full max-w-3xl px-4 py-8 flex flex-col flex-1">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold">
            Nexora Systems – AI Assistant
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Ask questions about Nexora documents or general AI topics.
          </p>
        </header>

        <div
          ref={chatWindowRef}
          className="flex-1 rounded-xl border border-slate-800 bg-slate-900/60 p-4 overflow-y-auto shadow-inner"
          style={{ maxHeight: "70vh" }}
        >
          {messages.length === 0 && (
            <p className="text-slate-500 text-sm">
              Start the conversation by asking, for example,{" "}
              <span className="italic">
                &quot;What does Nexora Systems do?&quot;
              </span>
            </p>
          )}
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`mb-4 flex ${
                m.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap ${
                  m.role === "user"
                    ? "bg-blue-600 text-white rounded-br-sm"
                    : "bg-slate-800 text-slate-100 rounded-bl-sm"
                }`}
              >
                <div>{m.content}</div>
                {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                  <div className="mt-2 text-xs text-slate-400 border-t border-slate-700 pt-2">
                    <div className="font-semibold mb-1">Sources:</div>
                    <ul className="list-disc list-inside space-y-0.5">
                      {m.sources.map((s, i) => (
                        <li key={i}>
                          {s.source || "unknown source"}
                          {typeof s.page !== "undefined" &&
                            s.page !== null &&
                            ` (page ${s.page})`}
                        </li>
                      ))}
                    </ul>
                    {typeof m.latency === "number" && (
                      <div className="mt-1">
                        Latency: {m.latency.toFixed(0)} ms
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="mt-2 text-xs text-slate-400">Thinking…</div>
          )}
        </div>

        <form
          onSubmit={sendMessage}
          className="mt-4 flex items-center gap-2 border border-slate-800 rounded-full bg-slate-900/90 px-3 py-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question…"
            className="flex-1 bg-transparent border-none outline-none text-sm text-slate-100 placeholder-slate-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-1.5 text-sm rounded-full bg-blue-600 hover:bg-blue-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-medium transition-colors"
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </form>
      </main>
    </div>
  );
}

