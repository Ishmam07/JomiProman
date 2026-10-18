import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../i18n.jsx";
import { Spinner } from "./common.jsx";

const SUGGESTIONS = ["chat.s1", "chat.s2", "chat.s3"];

export default function PlotChat({ mouza, dag }) {
  const { t } = useApp();
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    setMessages([]);
  }, [mouza, dag]);
  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [messages, busy]);

  async function send(text) {
    const q = text.trim();
    if (!q || busy) return;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const reply = await api.ask(mouza, dag, q);
      setMessages((m) => [...m, { role: "bot", text: reply.text, source: reply.source, model: reply.model }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "bot", text: e.message, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <div className="card-head">
        <h3>{t("chat.title")}</h3>
        <span className="badge">{t("chat.badge")}</span>
      </div>
      <div className="chips">
        {SUGGESTIONS.map((k) => (
          <button key={k} type="button" className="chip-btn" onClick={() => send(t(k))} disabled={busy}>
            {t(k)}
          </button>
        ))}
      </div>
      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`bubble bubble-${m.role} ${m.error ? "bubble-error" : ""}`}>
            {m.text}
            {m.source && (
              <div className="bubble-meta">{m.source === "ai" ? `AI · ${m.model}` : t("chat.auto")}</div>
            )}
          </div>
        ))}
        {busy && <Spinner label={t("chat.thinking")} />}
        <div ref={endRef} />
      </div>
      <form
        className="chat-form"
        onSubmit={(e) => {
          e.preventDefault();
          send(question);
        }}
      >
        <input
          value={question}
          maxLength={300}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("chat.ph")}
          aria-label={t("chat.aria")}
        />
        <button className="btn btn-primary" disabled={busy || !question.trim()}>
          {t("chat.send")}
        </button>
      </form>
      <p className="muted small">{t("chat.legal")}</p>
    </section>
  );
}
