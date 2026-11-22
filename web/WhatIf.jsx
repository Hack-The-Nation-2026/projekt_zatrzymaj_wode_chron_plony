import React from "react";

// Karta „Co da retencja na tej działce” (dane: report.whatIf z api.js, serwer: wodnik/whatif.py).
// Wymiarowanie działań na ulewę: ile wody spłynie i ile zatrzyma wał, obniżenie (oczko) i materia organiczna.

const fmt = (x, d = 0) => (x == null ? "b.d." : Number(x).toFixed(d).replace(".", ","));

export default function WhatIf({ w }) {
  if (!w) return null;
  return (
    <div className="step-card whatif">
      <div style={{ fontSize: 12, fontWeight: 700, color: "#555" }}>CO DA RETENCJA NA TEJ DZIAŁCE</div>
      <p style={{ fontSize: 14, margin: "8px 0 12px" }}>{w.summary}</p>

      <div className="whatif-storms">
        {w.storms.map((s) => (
          <div key={s.rain_mm}>
            <span>Ulewa {fmt(s.rain_mm)} mm</span>
            <b>{fmt(s.volume_total_m3)} m³ spływu</b>
          </div>
        ))}
      </div>

      <div className="whatif-measures">
        {w.measures.map((m) => (
          <div key={m.key} className="whatif-measure">
            <b>{m.key === "materia" ? "+" : ""}{fmt(m.value)} {m.unit}</b>
            <h4>{m.name}</h4>
            <p>{m.detail}</p>
          </div>
        ))}
      </div>

      <details className="whatif-assumptions">
        <summary>Jak to policzyliśmy</summary>
        <ul>{w.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
      </details>
    </div>
  );
}
