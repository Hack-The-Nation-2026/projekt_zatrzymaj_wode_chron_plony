import React from "react";
import * as charts from "./charts.js";

// Gotowe wykresy do raportu (dane: report.charts i report.scenarios z api.js → toView).
// Użycie w App.jsx (miejsce i wygląd do decyzji autora frontendu, propozycja w docs/UI.md):
//
//   import { HistoryChart, YearsChart } from "./Charts.jsx";
//   <YearsChart charts={report.charts} />                              // w karcie „Bilans wodny”
//   <HistoryChart charts={report.charts} scenarios={report.scenarios} /> // nad <Scenarios />
//
// Kolory i wielkość czcionki zmienia się w CSS zmiennymi --chart-* (lista na górze charts.js).
// Starsze raporty nie mają pola `charts`: wtedy komponenty nic nie rysują.

const Svg = ({ html }) => <div className="chart" dangerouslySetInnerHTML={{ __html: html }} />;
// SVG budujemy sami z liczb z serwera, a każdy tekst jest escapowany w charts.js.

/** Karta „Jak doszło do tej sytuacji”: zapas wody (z dalszym ciągiem scenariuszy) oraz opad i parowanie jeden pod drugim. */
export function HistoryChart({ charts: c, scenarios }) {
  if (!c?.daily) return null;
  return (
    <div className="step-card history-chart">
      <div style={{ fontSize: 12, fontWeight: 700, color: "#555", marginBottom: 8 }}>JAK DOSZŁO DO TEJ SYTUACJI?</div>

      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 4 }}>Woda w glebie</div>
      <Svg html={charts.water(c, scenarios)} />
      <div style={{ fontSize: 12, color: "#666", marginBottom: 18 }}>
        Zapas wody dostępnej dla roślin (bilans FAO-56). Po prawej: 30 dni naprzód, linia przerywana to typowy
        scenariusz, pasmo to rozrzut.
      </div>

      <div style={{ fontSize: 13, fontWeight: 600, marginTop: 12 }}>Opad i parowanie</div>
      <Svg html={charts.rainEt(c)} />
    </div>
  );
}

/** Mały wykres „ten rok na tle poprzednich lat” (bilans opad − parowanie z 60 dni). */
export function YearsChart({ charts: c }) {
  const html = charts.years(c);
  if (!html) return null;
  return (
    <div className="years-chart">
      <Svg html={html} />
      <div style={{ fontSize: 12, color: "#666" }}>
        {c.years.label}. Czerwona linia: próg roku z wyraźnym deficytem.
      </div>
    </div>
  );
}
