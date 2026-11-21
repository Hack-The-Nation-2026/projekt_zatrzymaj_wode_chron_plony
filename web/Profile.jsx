import React, { useEffect, useState } from "react";
import { api } from "./api.js";

// Profil: dane konta i historia zapisanych raportów (GET /api/v1/me, /me/reports).

const LEVEL = { niskie: "ok", umiarkowane: "warn", wysokie: "bad" };
const plDate = (s) => (s ? new Date(s).toLocaleDateString("pl-PL") : "");

export default function Profile({ user, onOpenReport, onBack }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState("");

  const load = () => api.listReports().then(setList).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const open = async (id) => {
    setError("");
    try { onOpenReport(await api.getReport(id)); } catch (e) { setError(e.message); }
  };
  const print = async (id) => {
    setError("");
    try { await api.openReportHtml(id); } catch (e) { setError(e.message); }
  };
  const remove = async (id) => {
    if (!window.confirm("Usunąć ten raport z historii?")) return;
    try { await api.deleteReport(id); load(); } catch (e) { setError(e.message); }
  };

  return (
    <main className="container">
      <section className="section" style={{ justifyContent: "flex-start" }}>
        <div className="eyebrow">Twoje konto</div>
        <h1>{user.name ? `Dzień dobry, ${user.name}` : "Twój profil"}</h1>
        <p className="sub">{user.email} · konto od {plDate(user.created_at)}</p>

        <div className="panel">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <h2>Historia raportów</h2>
            <button className="btn dark" onClick={onBack}>Nowa analiza</button>
          </div>
          {error && <p className="error-msg" role="alert">{error}</p>}
          {list === null && !error && <p className="sub" style={{ marginTop: 16 }}>Wczytuję…</p>}
          {list && list.length === 0 && (
            <p className="sub" style={{ marginTop: 16 }}>Brak zapisanych raportów. Zrób analizę, a pojawi się tutaj.</p>
          )}
          {list && list.length > 0 && (
            <ul className="history-list">
              {list.map((h) => (
                <li className="history-item" key={h.id}>
                  <div className="meta">
                    <b>{h.place || h.parcel_id}</b>
                    <span>{plDate(h.date)} · {h.crop} · zapisano {plDate(h.saved_at)}</span>
                  </div>
                  <span className={`badge ${LEVEL[h.risk_level] || "warn"}`}>Ryzyko: {h.risk_level}</span>
                  <button className="btn dark" onClick={() => open(h.id)}>Otwórz</button>
                  <button className="btn" onClick={() => print(h.id)}>Drukuj</button>
                  <button className="btn" onClick={() => remove(h.id)} aria-label="Usuń raport">Usuń</button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
}
