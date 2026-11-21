import React, { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// Asystent Wodnika: odpowiada na pytania o bieżący raport (serwer: POST /api/v1/chat, api/chat.py).

// Prosty, bezpieczny podgląd odpowiedzi: akapity, listy „- ” / „1. ” i pogrubienie **tekst** (bez HTML z modelu).
function inline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part);
}

function Rich({ text }) {
  const blocks = text.split(/\n{2,}/);
  return blocks.map((b, i) => {
    const lines = b.split("\n").filter((l) => l.trim());
    if (lines.length && lines.every((l) => /^\s*([-•*]|\d+[.)])\s+/.test(l))) {
      const ordered = /^\s*\d/.test(lines[0]);
      const items = lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*([-•*]|\d+[.)])\s+/, ""))}</li>);
      return ordered ? <ol key={i}>{items}</ol> : <ul key={i}>{items}</ul>;
    }
    return <p key={i}>{lines.map((l, j) => <React.Fragment key={j}>{j > 0 && <br />}{inline(l.replace(/^#+\s*/, ""))}</React.Fragment>)}</p>;
  });
}

const SUGGESTIONS = [
  "Co powinienem zrobić najpierw?",
  "Dlaczego ryzyko jest takie, a nie inne?",
  "Czy opłaca mi się nawadniać?",
  "Jak zatrzymać więcej wody na polu?",
];

export default function Chat({ report }) {
  const [messages, setMessages] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [aiOff, setAiOff] = useState(false);
  const logRef = useRef(null);

  // Nowy raport = nowa rozmowa.
  useEffect(() => { setMessages([]); setAiOff(false); }, [report?.id, report?.historyId]);
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" }); }, [messages, busy]);

  const ask = async (q) => {
    const question = q.trim();
    if (!question || busy) return;
    const next = [...messages, { role: "user", content: question }];
    setMessages(next);
    setText("");
    setBusy(true);
    try {
      const r = await api.chat({ messages: next, report });
      setAiOff(r.source !== "ai");
      setMessages([...next, { role: "assistant", content: r.reply }]);
    } catch (e) {
      setMessages([...next, { role: "assistant", content: `Nie udało się uzyskać odpowiedzi: ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="chat">
      <div className="chat-head">
        <b>Zapytaj asystenta o ten raport</b>
        <span>{aiOff ? "tryb podstawowy: skrót z raportu" : "odpowiedzi na podstawie danych z raportu"}</span>
      </div>
      {(messages.length > 0 || busy) && (
        <div className="chat-log" ref={logRef} aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>{m.role === "assistant" ? <Rich text={m.content} /> : m.content}</div>
          ))}
          {busy && <div className="chat-msg assistant pending">Asystent pisze…</div>}
        </div>
      )}
      {messages.length === 0 && (
        <div className="chat-suggest" style={{ paddingTop: 12 }}>
          {SUGGESTIONS.map((s) => <button key={s} type="button" onClick={() => ask(s)}>{s}</button>)}
        </div>
      )}
      <form className="chat-form" onSubmit={(e) => { e.preventDefault(); ask(text); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={2000}
               placeholder="Np. czy warto zrobić oczko wodne na tej działce?" aria-label="Pytanie do asystenta" />
        <button className="btn dark" disabled={busy || !text.trim()}>Wyślij</button>
      </form>
      <p className="chat-note">Asystent AI może się mylić. Ważne decyzje, zwłaszcza o rowach, stawach i poborze wody, skonsultuj z doradcą ODR.</p>
    </div>
  );
}
