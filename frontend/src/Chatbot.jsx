import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const CHAT_SHARED_SECRET = import.meta.env.VITE_CHAT_SHARED_SECRET || "";

export default function Chatbot({ dark = false, articleContext = [] }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    const text = query.trim();
    if (!text || busy) return;

    const nextMessages = [...messages, { role: "user", content: text }];
    setMessages(nextMessages);
    setQuery("");
    setError("");
    setBusy(true);

    try {
      const headers = { "Content-Type": "application/json" };
      if (CHAT_SHARED_SECRET) headers["X-Chat-Secret"] = CHAT_SHARED_SECRET;
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          query: text,
          history: nextMessages.slice(-6),
          article_context: articleContext.slice(0, 20),
        }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Chat request failed.");
      setMessages([...nextMessages, { role: "assistant", content: body.response }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={`chatbot ${dark ? "chatbot-dark" : ""}`}>
      {open && (
        <section className="chat-panel" aria-label="Ask Meridian chatbot">
          <header className="chat-header">
            <div>
              <strong>Ask Meridian</strong>
              <span>Your healthcare AI assistant</span>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close chatbot">
              ×
            </button>
          </header>
          <div className="chat-messages" aria-live="polite">
            {messages.length === 0 && (
              <p className="chat-empty">Ask about healthcare news and industry intelligence.</p>
            )}
            {messages.map((message, index) => (
              <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                {message.content}
              </div>
            ))}
            {busy && <div className="chat-message assistant">Connecting to Meridian...</div>}
          </div>
          <div className="chat-footer">
            {error && <p className="chat-error">{error}</p>}
            <form onSubmit={submit}>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Ask anything..."
                aria-label="Message"
                disabled={busy}
              />
              <button type="submit" disabled={busy || !query.trim()}>Send</button>
            </form>
            <button type="button" className="clear-chat" onClick={() => setMessages([])}>
              Clear chat
            </button>
          </div>
        </section>
      )}
      <button
        type="button"
        className="chat-launcher"
        onClick={() => setOpen(!open)}
        aria-label={open ? "Close chatbot" : "Open chatbot"}
      >
        {open ? "×" : "💬"}
      </button>
    </div>
  );
}
