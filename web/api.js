// Połączenie frontendu z serwerem Wodnika (FastAPI, docs/API.md).
// Ma te same funkcje co wcześniejsze dummyApi, więc App.jsx zmienia się minimalnie.
// W trybie `npm run dev` zapytania /api przekazuje do serwera proxy z vite.config.js.

const API = "/api/v1";
const TOKEN_KEY = "wodnik_token";

// Token sesji (logowanie). Brak dostępu do localStorage (tryb prywatny) nie psuje aplikacji.
let token = null;
try { token = localStorage.getItem(TOKEN_KEY); } catch { /* bez zapamiętania */ }
function setToken(t) {
  token = t;
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* j.w. */ }
}

async function call(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  const r = await fetch(API + path, { ...opts, headers });
  if (r.status === 401 && token && !path.startsWith("/auth/")) setToken(null); // sesja wygasła
  if (r.status === 204) return null;
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
  const seen = new Set();
  const uniqueSteps = steps.filter((x) => {
    const key = `${x.step}|${x.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
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
    recommendations: uniqueSteps.map((x) => ({ step: x.step, title: x.title, detail: x.detail, confidence: x.confidence })),
    raw: {
      kbw60_mm: num(raw.kbw60_mm, 1, "mm"),
      depletion_mm: num(raw.wyczerpanie_mm, 1, "mm"),
      taw_mm: num(raw.TAW_mm, 1, "mm"),
      percentile: raw.wilgotnosc_percentyl != null
        ? `wilgotność gleby: w ${num(raw.wilgotnosc_percentyl, 0)}% z ostatnich ${raw.lata_referencyjne} lat było tak samo sucho lub suszej`
        : "brak danych o wilgotności gleby dla tej daty",
    },
    scenarios: report.scenarios || null,
    charts: report.charts || null, // dane do wykresów (Charts.jsx), brak w starszych raportach
    whatIf: report.what_if || null, // „co da retencja” (WhatIf.jsx), brak w starszych raportach
    full: report, // pełny wynik: ocena, uzasadnienia, niepewność, źródła
  };
}

function parcelView(p) {
  return { id: p.id, commune: p.commune, region: `${p.region} (${p.id.split(".").pop()})`,
           area_ha: p.area_ha, center: p.center, geometry: p.geometry };
}

const jsonPost = (path, data) =>
  call(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });

export const api = {
  // --- konto ---
  isLoggedIn: () => Boolean(token),
  /** Zakłada konto i od razu loguje. Zwraca { id, email, name, created_at }. */
  register: async ({ email, password, name }) => {
    const r = await jsonPost("/auth/register", { email, password, name: name || null });
    setToken(r.token);
    return r.user;
  },
  login: async ({ email, password }) => {
    const r = await jsonPost("/auth/login", { email, password });
    setToken(r.token);
    return r.user;
  },
  logout: async () => {
    try { await call("/auth/logout", { method: "POST" }); } finally { setToken(null); }
  },
  /** Zalogowany użytkownik albo null. */
  me: async () => (token ? call("/me").catch(() => null) : null),

  // --- historia raportów (profil) ---
  /** Lista: [{ id, parcel_id, place, date, crop, risk_level, saved_at }], najnowsze pierwsze. */
  listReports: () => call("/me/reports"),
  /** Pełny raport z historii w tym samym formacie co wynik runAnalysis. */
  getReport: async (id) => {
    const r = await call(`/me/reports/${id}`);
    const p = r.report.parcel || {};
    const parcel = { id: p.id, commune: p.gmina, region: p.obreb, area_ha: p.powierzchnia_ha,
                     center: p.srodek, geometry: p.geometria_wgs84 };
    return { ...toView(r.report, parcel, { name: r.report.crop }, r.analysis_id), historyId: r.id };
  },
  deleteReport: (id) => call(`/me/reports/${id}`, { method: "DELETE" }),
  /** Otwiera raport z historii do druku w nowej karcie (wymaga zalogowania). */
  openReportHtml: async (id) => {
    const r = await fetch(`${API}/me/reports/${id}/raport`, { headers: { Authorization: `Bearer ${token}` } });
    if (!r.ok) throw new Error("Nie udało się otworzyć raportu.");
    window.open(URL.createObjectURL(await r.blob()), "_blank");
  },

  searchParcelById: async (id) => parcelView(await call(`/parcels/by-id?id=${encodeURIComponent(id)}`)),

  resolveParcelByCoords: async (lat, lon) =>
    parcelView(await call(`/parcels/resolve?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lon)}`)),

  // --- asystent ---
  /** Czat o raporcie. messages: [{ role: "user" | "assistant", content }], report: model widoku z runAnalysis
   *  lub getReport (albo null). Zwraca { reply, source: "ai" | "fallback" }. */
  chat: ({ messages, report }) =>
    jsonPost("/chat", {
      messages,
      ...(report?.historyId ? { report_id: report.historyId } : report?.id ? { analysis_id: report.id } : {}),
    }),

  // --- analiza ---
  /** Uruchamia analizę i czeka na wynik; onProgress(lista etapów) przy każdym odpytaniu.
   *  Gdy użytkownik jest zalogowany, wynik trafia też do jego historii. */
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
