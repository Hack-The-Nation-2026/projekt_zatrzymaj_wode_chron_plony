import React from "react";

// Karta „Co dalej: najbliższe 30 dni” – scenariusze z 31 lat (wodnik/scenarios.py).
// Wykres pokazuje zapas wody dostępnej dla roślin (mm): pasmo = od suchych (10%) do mokrych (90%) scenariuszy,
// linia = scenariusz typowy (mediana), przerywana = próg, poniżej którego roślina jest w stresie.

const fmt = (x, d = 0) => (x == null ? "b.d." : Number(x).toFixed(d).replace(".", ","));
const LEVEL_CLASS = { niskie: "ok", umiarkowane: "warn", wysokie: "bad" };

function Chart({ s }) {
  const W = 560, H = 200, L = 40, R = 12, T = 24, B = 28;
  const env = s.envelope;
  const taw = s.taw_mm;
  const x = (day) => L + ((day - 1) / Math.max(1, env.length - 1)) * (W - L - R);
  const y = (water) => T + (1 - Math.max(0, Math.min(taw, water)) / taw) * (H - T - B);
  const left = (dr) => taw - dr; // zapas wody = TAW − wyczerpanie
  const band =
    env.map((d) => `${x(d.day)},${y(left(d.p10))}`).join(" ") + " " +
    [...env].reverse().map((d) => `${x(d.day)},${y(left(d.p90))}`).join(" ");
  const median = env.map((d) => `${x(d.day)},${y(left(d.p50))}`).join(" ");
  const stressY = y(taw - s.raw_mm);
  const ticks = [0, Math.round(taw / 2), Math.round(taw)];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img"
         aria-label="Zapas wody w glebie w najbliższych 30 dniach w scenariuszach pogodowych">
      <rect x={L} y={stressY} width={W - L - R} height={H - B - stressY} fill="#3a1f24" opacity="0.55" />
      {ticks.map((t) => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} stroke="#22394d" />
          <text x={L - 6} y={y(t) + 4} fontSize="11" fill="#9db0c0" textAnchor="end">{t}</text>
        </g>
      ))}
      <polygon points={band} fill="#4d8b3c" opacity="0.35" />
      <polyline points={median} fill="none" stroke="#63b34e" strokeWidth="2.5" />
      <line x1={L} x2={W - R} y1={stressY} y2={stressY} stroke="#ff8a80" strokeDasharray="5 4" strokeWidth="1.5" />
      <text x={W - R} y={stressY - 5} fontSize="11" fill="#ff8a80" textAnchor="end">próg stresu</text>
      {[1, 7, 14, 21, 30].filter((d) => d <= env.length).map((d) => (
        <text key={d} x={x(d)} y={H - 8} fontSize="11" fill="#9db0c0" textAnchor="middle">{d === 1 ? "dzień 1" : d}</text>
      ))}
      <text x={L - 6} y={11} fontSize="11" fill="#9db0c0" textAnchor="end">mm</text>
    </svg>
  );
}

export default function Scenarios({ s }) {
  if (!s) return null;
  const pct = (p) => `${fmt(p * 100)}%`;
  return (
    <div className="step-card scenarios">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: "#555" }}>
          CO DALEJ: NAJBLIŻSZE {s.horizon_days} DNI ({s.years} SCENARIUSZY POGODOWYCH)
        </div>
        <span className={`badge ${LEVEL_CLASS[s.level] || "warn"}`}>Ryzyko w najbliższych tygodniach: {s.level}</span>
      </div>
      <p style={{ fontSize: 14, margin: "8px 0 10px" }}>{s.summary}</p>
      <div className="scen-stats">
        {s.in_stress_now ? (
          <div><b>{pct(s.p_recovery_30)}</b><span>szansa, że stres ustąpi w {s.horizon_days} dni</span></div>
        ) : (
          <>
            <div><b>{pct(s.p_stress_14)}</b><span>szansa stresu w 14 dni</span></div>
            <div><b>{pct(s.p_stress_30)}</b><span>szansa stresu w {s.horizon_days} dni</span></div>
          </>
        )}
        <div><b>{pct(s.p_severe_30)}</b><span>szansa silnego stresu</span></div>
        <div>
          <b>{fmt(s.water_needed_p50_mm)} mm</b>
          <span>wody, by uniknąć stresu (w suchym scenariuszu {fmt(s.water_needed_p90_mm)} mm)</span>
        </div>
      </div>
      <Chart s={s} />
      <div style={{ fontSize: 12, color: "#9db0c0" }}>
        Zapas wody dostępnej dla roślin. Pasmo: od suchych do mokrych scenariuszy, linia: scenariusz typowy.
        {s.forecast_days_used > 0 && ` Pierwsze ${s.forecast_days_used} dni z prognozy pogody.`} To nie jest prognoza
        konkretnej pogody, tylko rozkład możliwych przebiegów na podstawie lat 1995–2025.
      </div>
    </div>
  );
}
