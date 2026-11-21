// Połączenie frontendu z serwerem Wodnika (FastAPI, docs/API.md).
// Ma te same funkcje co wcześniejsze dummyApi, więc App.jsx zmienia się minimalnie.
// W trybie `npm run dev` zapytania /api przekazuje do serwera proxy z vite.config.js.

const API = "/api/v1";

async function call(path, opts) {
  const r = await fetch(API + path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = body.error || {};
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ") : "";
    throw new Error([e.message || detail || `Błąd serwera (${r.status})`, e.hint].filter(Boolean).join(" "));
  }
  return body;
}

const num = (x, d = 1, unit = "") =>
  x == null ? "b.d." : `${Number(x).toFixed(d).replace(".", ",").replace("-", "−")}${unit ? " " + unit : ""}`;
const cap = (s = "") => s.charAt(0).toUpperCase() + s.slice(1);

/** Tłumaczy pełny raport z serwera na model widoku używany w App.jsx. */
export function toView(report, parcel, crop, id) {
  const causes = report.causes || [];
  const main = causes.find((c) => c.name === report.main_cause) || causes[0];
  const second = causes.find((c) => c !== main && c.strength !== "słaba");
  const raw = report.raw || {};
  const steps = [
    ...report.retention.filter((x) => x.priority <= 2).map((x) => ({ ...x, step: "1. Retencja" })),
    ...report.agrotechnics.filter((x) => x.priority <= 2).map((x) => ({ ...x, step: "2. Agrotechnika" })),
    ...report.irrigation.map((x) => ({ ...x, step: "3. Nawadnianie (ostateczność)" })),
  ];
  return {
    id,
    parcel,
    crop,
    date: report.date,
    risk_level: cap(report.risk_level),
    risk_summary: report.risk_summary,
    confidence: report.confidence,
    main_cause: main ? `${main.name} (${main.because[0]})` : "Brak wyraźnej przyczyny",
    secondary_cause: second ? `${second.name} (${second.because[0]})` : "Brak drugorzędnych przyczyn",
    recommendations: steps.map((x) => ({ step: x.step, title: x.title, detail: x.detail, confidence: x.confidence })),
    raw: {
      kbw60_mm: num(raw.kbw60_mm, 1, "mm"),
      depletion_mm: num(raw.wyczerpanie_mm, 1, "mm"),
      taw_mm: num(raw.TAW_mm, 1, "mm"),
      percentile: raw.wilgotnosc_percentyl != null
        ? `tak sucho było w ${num(raw.wilgotnosc_percentyl, 0)}% lat (z ${raw.lata_referencyjne} lat)`
        : "brak danych o wilgotności gleby dla tej daty",
    },
    scenarios: report.scenarios || null,
    full: report, // pełny wynik: ocena, uzasadnienia, niepewność, źródła
  };
}

function parcelView(p) {
  return { id: p.id, commune: p.commune, region: `${p.region} (${p.id.split(".").pop()})`,
           area_ha: p.area_ha, center: p.center, geometry: p.geometry };
}

export const api = {
  searchParcelById: async (id) => parcelView(await call(`/parcels/by-id?id=${encodeURIComponent(id)}`)),

  resolveParcelByCoords: async (lat, lon) =>
    parcelView(await call(`/parcels/resolve?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)),

  /** Uruchamia analizę i czeka na wynik; onProgress(lista etapów) przy każdym odpytaniu. */
  runAnalysis: async ({ parcel, crop, date, onProgress }) => {
    const job = await call("/analyses", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parcel_id: parcel.id, crop: crop.key, date: date || null }),
    });
    let a;
    do {
      a = await call(`/analyses/${job.id}`);
      onProgress?.(a.progress);
      if (a.status === "running") await new Promise((r) => setTimeout(r, 1200));
    } while (a.status === "running");
    if (a.status === "failed") {
      throw new Error([a.error?.message || "Analiza się nie powiodła.", a.error?.hint].filter(Boolean).join(" "));
    }
    return toView(a.report, parcel, crop, job.id);
  },
};
