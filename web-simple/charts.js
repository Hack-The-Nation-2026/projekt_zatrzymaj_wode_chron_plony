// Wykresy wyniku analizy jako tekst SVG (bez bibliotek, bez Reacta).
// Ten sam plik jest w web/ (frontend React) i web-simple/ (widok /prosty). Odpowiednik dla raportu do druku:
// wodnik/charts.py. Dane: pole `charts` z wyniku analizy (docs/API.md), scenariusze: pole `scenarios`.
//
// Kolory można zmienić w CSS bez ruszania tego pliku, np.:
//   .wodnik-chart { --chart-font:14px; --chart-ink:#e6edf3; --chart-muted:#9db0c0; --chart-grid:#22394d; --chart-stress-bg:#3a1f24 }

const W = 720, H = 230, L = 46, R = 14, T = 28, B = 30;
const C = {
  ink: "var(--chart-ink, #1b2e30)", muted: "var(--chart-muted, #5b6b6d)", grid: "var(--chart-grid, #e3e8e4)",
  water: "var(--chart-water, #1d5f9a)", stress: "var(--chart-stress, #c0392b)", stressBg: "var(--chart-stress-bg, #fbe9e7)",
  rain: "var(--chart-rain, #2f7fc1)", et: "var(--chart-et, #e08a1e)", bad: "var(--chart-bad, #c0392b)",
  year: "var(--chart-year, #9bb7a0)",
};

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const f = (n) => n.toFixed(1);
const num = (n) => Math.round(n).toString().replace("-", "−");
const txt = (x, y, s, anchor = "start", color = C.muted, extra = "") =>
  `<text x="${f(x)}" y="${f(y)}" fill="${color}" text-anchor="${anchor}" ${extra}>${esc(s)}</text>`;
const svg = (body, label, h = H) =>
  `<svg class="wodnik-chart" viewBox="0 0 ${W} ${h}" width="100%" role="img" aria-label="${esc(label)}" ` +
  `style="font-family:system-ui,Arial,sans-serif;font-size:var(--chart-font, 11px);max-width:${W}px">${body}</svg>`;

function monthTicks(dates, x) {
  return dates.map((d, i) => d.slice(8, 10) === "01"
    ? `<line x1="${f(x(i))}" x2="${f(x(i))}" y1="${T}" y2="${H - B}" stroke="${C.grid}"/>` +
      txt(x(i), H - B + 16, `${d.slice(8, 10)}.${d.slice(5, 7)}`, "middle")
    : "").join("");
}

/** Wykres 1: zapas wody dostępnej dla roślin w ostatnich miesiącach + 30 dni scenariuszy (gdy są). */
export function water(charts, scenarios) {
  if (!charts?.daily) return "";
  const dd = charts.daily, dates = dd.dates, left = dd.water_left_mm;
  const taw = dd.taw_mm || 1, stress = dd.stress_below_mm;
  const env = scenarios?.envelope || [];
  const n = dates.length + env.length;
  const x = (i) => L + (i / Math.max(1, n - 1)) * (W - L - R);
  const y = (v) => T + (1 - Math.max(0, Math.min(taw, v)) / taw) * (H - T - B);
  const iNow = dates.length - 1;
  let p = `<rect x="${L}" y="${f(y(stress))}" width="${W - L - R}" height="${f(H - B - y(stress))}" fill="${C.stressBg}"/>`;
  for (const t of [0, Math.round(taw / 2), Math.round(taw)]) {
    p += `<line x1="${L}" x2="${W - R}" y1="${f(y(t))}" y2="${f(y(t))}" stroke="${C.grid}"/>` + txt(L - 6, y(t) + 4, t, "end");
  }
  p += monthTicks(dates, x);
  p += `<line x1="${L}" x2="${W - R}" y1="${f(y(stress))}" y2="${f(y(stress))}" stroke="${C.stress}" stroke-dasharray="5 4"/>`;
  p += txt(L + 4, y(stress) + 13, "poniżej: roślina w stresie wodnym", "start", C.stress);
  p += `<polyline points="${left.map((v, i) => (v == null ? "" : `${f(x(i))},${f(y(v))}`)).join(" ")}" fill="none" stroke="${C.water}" stroke-width="2.2"/>`;
  p += `<line x1="${f(x(iNow))}" x2="${f(x(iNow))}" y1="${T}" y2="${H - B}" stroke="${C.ink}"/>`;
  p += txt(x(iNow) - 4, T + 12, "dziś", "end", C.ink, 'font-weight="700"');
  if (env.length) {
    const k = (day) => x(iNow + day);
    const band = env.map((e) => `${f(k(e.day))},${f(y(taw - e.p10))}`).join(" ") + " " +
      [...env].reverse().map((e) => `${f(k(e.day))},${f(y(taw - e.p90))}`).join(" ");
    const med = env.map((e) => `${f(k(e.day))},${f(y(taw - e.p50))}`).join(" ");
    p += `<polygon points="${band}" fill="${C.water}" opacity="0.18"/>`;
    p += `<polyline points="${f(x(iNow))},${f(y(left[iNow] ?? 0))} ${med}" fill="none" stroke="${C.water}" stroke-width="2" stroke-dasharray="6 3"/>`;
    p += txt(W - R, 12, "30 dni: scenariusze", "end");
  }
  p += txt(L - 6, 12, "mm", "end");
  return svg(p, "Zapas wody w glebie dostępnej dla roślin w ostatnich miesiącach i scenariusze na 30 dni");
}

/** Wykres 2: opad dzienny (słupki) i parowanie ET0 (linia). */
export function rainEt(charts) {
  if (!charts?.daily) return "";
  const dd = charts.daily, dates = dd.dates;
  const pr = dd.precip_mm.map((v) => v || 0), et = dd.et0_mm.map((v) => v || 0);
  const top = Math.max(10, Math.max(...pr, ...et) * 1.1);
  const n = dates.length;
  const x = (i) => L + ((i + 0.5) / n) * (W - L - R);
  const y = (v) => T + (1 - Math.min(top, v) / top) * (H - T - B);
  const bw = Math.max(1, ((W - L - R) / n) * 0.75);
  let p = "";
  for (const t of [0, Math.round(top / 2), Math.round(top)]) {
    p += `<line x1="${L}" x2="${W - R}" y1="${f(y(t))}" y2="${f(y(t))}" stroke="${C.grid}"/>` + txt(L - 6, y(t) + 4, t, "end");
  }
  p += monthTicks(dates, x);
  p += pr.map((v, i) => (v > 0 ? `<rect x="${f(x(i) - bw / 2)}" y="${f(y(v))}" width="${f(bw)}" height="${f(y(0) - y(v))}" fill="${C.rain}"/>` : "")).join("");
  p += `<polyline points="${et.map((v, i) => `${f(x(i))},${f(y(v))}`).join(" ")}" fill="none" stroke="${C.et}" stroke-width="2"/>`;
  const sp = pr.reduce((a, b) => a + b, 0), se = et.reduce((a, b) => a + b, 0);
  p += txt(W - R, 12, `opad ${num(sp)} mm · parowanie ${num(se)} mm · bilans ${sp - se >= 0 ? "+" : ""}${num(sp - se)} mm`, "end", C.ink);
  p += `<rect x="${L + 4}" y="3" width="10" height="10" fill="${C.rain}"/>` + txt(L + 18, 12, "opad");
  p += `<line x1="${L + 60}" x2="${L + 74}" y1="8" y2="8" stroke="${C.et}" stroke-width="2"/>` + txt(L + 78, 12, "parowanie (ET0)");
  p += txt(L - 6, 12, "mm/d", "end");
  return svg(p, "Opad dzienny i parowanie w ostatnich miesiącach");
}

/** Wykres 3: bilans opad − parowanie z 60 dni w kolejnych latach, rok analizy wyróżniony. */
export function years(charts) {
  const yy = charts?.years;
  const items = (yy?.items || []).filter((i) => i.kbw60_mm != null);
  if (!items.length) return "";
  const h = 200, thr = yy.deficit_threshold_mm;
  const vals = [...items.map((i) => i.kbw60_mm), thr, 0];
  const lo = Math.min(...vals) * 1.1, hi = Math.max(Math.max(...vals) * 1.1, 10);
  const n = items.length;
  const x = (i) => L + ((i + 0.5) / n) * (W - L - R);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (h - T - B);
  const bw = ((W - L - R) / n) * 0.62;
  let p = `<line x1="${L}" x2="${W - R}" y1="${f(y(0))}" y2="${f(y(0))}" stroke="${C.ink}"/>` + txt(L - 6, y(0) + 4, 0, "end");
  p += `<line x1="${L}" x2="${W - R}" y1="${f(y(thr))}" y2="${f(y(thr))}" stroke="${C.bad}" stroke-dasharray="5 4"/>`;
  p += txt(L - 6, y(thr) + 4, num(thr), "end", C.bad);
  items.forEach((it, i) => {
    const v = it.kbw60_mm;
    const color = it.current ? C.ink : v <= thr ? C.bad : C.year;
    const [y0, y1] = [y(0), y(v)].sort((a, b) => a - b);
    p += `<rect x="${f(x(i) - bw / 2)}" y="${f(y0)}" width="${f(bw)}" height="${f(Math.max(1, y1 - y0))}" fill="${color}"/>`;
    p += txt(x(i), h - B + 14, it.current ? `${it.year} (ten rok)` : it.year, "middle",
      it.current ? C.ink : C.muted, it.current ? 'font-weight="700"' : "");
    p += txt(x(i), v < 0 ? y1 + 12 : y0 - 4, num(v), "middle");
  });
  p += txt(L - 6, 12, "mm", "end");
  return svg(p, "Bilans wody z 60 dni w tym roku na tle poprzednich lat", h);
}
