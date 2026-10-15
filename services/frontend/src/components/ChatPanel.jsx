import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { sendChatMessage } from "../api";

const SUGGESTIONS = [
  "Why did I spend more this month than last month?",
  "Am I within my budget this month?",
  "Any unusual spending this month?",
];

const newThreadId = () => `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

export default function ChatPanel() {
  const [messages, setMessages] = useState([]); // { role: "user" | "assistant" | "error", text, tools? }
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const threadId = useRef(newThreadId()); // the agent remembers the conversation per thread id
  const listRef = useRef(null);

  // Keep the newest message in view
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  async function send(text) {
    const message = text.trim();
    if (!message || busy) return;
    setMessages((prev) => [...prev, { role: "user", text: message }]);
    setInput("");
    setBusy(true);
    try {
      const reply = await sendChatMessage(message, threadId.current);
      const tools = [...new Set(reply.tools_used.map((t) => t.name))];
      setMessages((prev) => [...prev, { role: "assistant", text: reply.answer, tools }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "error", text: err.message }]);
    } finally {
      setBusy(false);
    }
  }

  function newChat() {
    threadId.current = newThreadId();
    setMessages([]);
  }

  return (
    <section className="panel chat">
      <div className="panel-head">
        <h3>Ask SmartSpend</h3>
        {messages.length > 0 && (
          <button type="button" className="link" onClick={newChat}>New chat</button>
        )}
      </div>

      <div className="chat-messages" ref={listRef} aria-live="polite">
        {messages.length === 0 && (
          <div className="chips">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="chip" onClick={() => send(s)}>{s}</button>
            ))}
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            {m.role === "assistant" ? <ReactMarkdown>{m.text}</ReactMarkdown> : <p>{m.text}</p>}
            {m.tools?.length > 0 && <div className="tools">Used: {m.tools.join(", ")}</div>}
          </div>
        ))}

        {busy && <div className="msg assistant thinking">Thinking…</div>}
      </div>

      <div className="chat-input">
        <input
          type="text"
          aria-label="Message"
          placeholder='Ask about your spending, e.g. "compare October 2026 with September"'
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send(input)}
        />
        <button type="button" className="primary" disabled={busy || !input.trim()} onClick={() => send(input)}>
          Send
        </button>
      </div>
    </section>
  );
}