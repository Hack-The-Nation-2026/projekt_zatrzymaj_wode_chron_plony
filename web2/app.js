// Wodnik – podstawowy interfejs. Rozmawia z serwerem FastAPI (docs/API.md).
const API = "/api/v1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let selected = null;      // wybrana działka (id + geometria)
let parcelLayer = null;   // obrys działki na mapie
let markers = L.layerGroup();

// --- mapa ---------------------------------------------------------------------
const map = L.map("map", { zoomControl: true }).setView([52.0, 19.4], 6);
const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, attribution: "© OpenStreetMap",
});
const orto = L.tileLayer.wms("https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution", {
  layers: "Raster", format: "image/jpeg", maxZoom: 19, attribution: "Ortofotomapa © GUGiK",
});
const parcels = L.tileLayer.wms("https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow", {
  layers: "dzialki,numery_dzialek", format: "image/png", transparent: true, minZoom: 15, maxZoom: 19,
  attribution: "Działki © GUGiK",
});
orto.addTo(map);
parcels.addTo(map);
markers.addTo(map);
L.control.layers({ "Zdjęcie lotnicze": orto, "Mapa": osm }, { "Granice działek": parcels }).addTo(map);

map.on("click", async (e) => {
  showError("");
  try {
    const p = await api(`/parcels/resolve?lat=${e.latlng.lat}&lon=${e.latlng.lng}`);
    selectParcel(p);
  } catch (err) { showError(err.message); }
});

// --- komunikacja z API -------------------------------------------------------
async function api(path, opts) {
  const r = await fetch(API + path, opts);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    const e = body.error || (body.detail && { message: body.detail.map?.((d) => d.msg).join("; ") }) || {};
    throw new Error(e.message || `Błąd serwera (${r.status})`);
  }
  return body;
}

function showError(msg) {
  $("formError").textContent = msg;
  $("formError").hidden = !msg;
}

// --- wybór działki ------------------------------------------------------------
function selectParcel(p) {
  selected = p;
  $("result").hidden = true;      // wynik dotyczył poprzedniej działki
  $("progress").hidden = true;
  markers.clearLayers();
  $("parcelId").value = p.id;
  $("parcelInfo").hidden = false;
  $("parcelInfo").innerHTML = `<b>${esc(p.region)}</b>, gm. ${esc(p.commune)} · ${fmt(p.area_ha, 2)} ha<br><span class="note">${esc(p.id)}</span>`;
  $("goBtn").disabled = false;
  if (parcelLayer) map.removeLayer(parcelLayer);
  parcelLayer = L.geoJSON(p.geometry, { style: { color: "#e8b13a", weight: 3, fillOpacity: 0.12 } }).addTo(map);
  map.fitBounds(parcelLayer.getBounds(), { maxZoom: 17, padding: [30, 30] });
}

$("findBtn").addEventListener("click", async () => {
  showError("");
  const id = $("parcelId").value.trim();
  if (!id) return showError("Wpisz numer działki albo dotknij jej na mapie.");
  try { selectParcel(await api(`/parcels/by-id?id=${encodeURIComponent(id)}`)); }
  catch (err) { showError(err.message); }
});

$("demoBtn").addEventListener("click", async () => {
  $("parcelId").value = "101609_2.0011.352";
  $("date").value = "2026-06-15";
  $("crop").value = "pszenica_ozima";
  $("findBtn").click();
});

// --- analiza ------------------------------------------------------------------
$("form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  if (!selected) return;
  showError("");
  $("goBtn").disabled = true;
  $("result").hidden = true;
  markers.clearLayers();
  try {
    const job = await api("/analyses", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parcel_id: selected.id, date: $("date").value || null, crop: $("crop").value }),
    });
    $("progress").hidden = false;
    let a;
    do {
      a = await api(`/analyses/${job.id}`);
      renderSteps(a.progress);
      if (a.status === "running") await new Promise((r) => setTimeout(r, 1200));
    } while (a.status === "running");
    if (a.status === "failed") {
      throw new Error([a.error?.message || "Analiza się nie powiodła.", a.error?.hint].filter(Boolean).join(" "));
    }
    $("progress").hidden = true;
    renderResult(a.report);
  } catch (err) {
    showError(err.message);
  } finally {
    $("goBtn").disabled = false;
  }
});

function renderSteps(steps) {
  $("steps").innerHTML = steps.map((s) => `<li class="${s.state}">${esc(s.label)}</li>`).join("");
}

// --- wynik --------------------------------------------------------------------
const fmt = (n, d = 0) => (n == null ? "b.d." : Number(n).toFixed(d).replace(".", ","));

function itemHtml(it, group) {
  const loc = it.location
    ? `<button type="button" class="secondary" data-lat="${it.location.lat}" data-lon="${it.location.lon}" data-title="${esc(it.title)}">📍 Pokaż na mapie</button>`
    : "";
  const why = it.because?.length
    ? `<details class="why"><summary>Dlaczego tak?</summary><ul>${it.because.map((b) => `<li>${esc(b)}</li>`).join("")}</ul></details>`
    : "";
  if (it.location) addMarker(it, group);
  return `<div class="item"><h3>${esc(it.title)}</h3><p>${esc(it.detail)}</p>
    <span class="badge ${esc(it.confidence)}">pewność: ${esc(it.confidence)}</span>${why}${loc}</div>`;
}

function stage(n, title, items, group, open = false, last = false) {
  return `<details class="stage${last ? " last" : ""}" ${open ? "open" : ""}>
    <summary><span class="num">${n}</span>${esc(title)}</summary>
    <div class="stage-body">${items.map((it) => itemHtml(it, group)).join("") || '<p class="note">Brak zaleceń.</p>'}</div></details>`;
}

function causesHtml(causes) {
  return causes.map((c) => ({
    title: c.name, detail: `Siła: ${c.strength}.`, because: c.because, confidence: "średnia",
  }));
}

function renderResult(r) {
  const d = new Date(r.date).toLocaleDateString("pl-PL");
  const main = r.main_cause ? `<p class="cause">Główna przyczyna: ${esc(r.main_cause)}</p>` : "";
  const others = r.causes.filter((c) => c.name !== r.main_cause && c.strength !== "słaba").map((c) => esc(c.name.toLowerCase()));
  const top = [...r.retention, ...r.agrotechnics].filter((x) => x.priority === 1).slice(0, 3);

  $("result").innerHTML = `
    <div class="risk ${esc(r.risk_level)}">
      <div class="label">Ryzyko suszy</div>
      <div class="level">${esc(r.risk_level.toUpperCase())}</div>
      <p>${esc(r.risk_summary)}</p>
    </div>
    <p class="meta">${esc(r.parcel.obreb)}, gm. ${esc(r.parcel.gmina)} · ${fmt(r.parcel.powierzchnia_ha, 2)} ha · ${d} · ${esc(r.crop)} · pewność analizy: <b>${esc(r.confidence)}</b></p>
    <div class="card">${main}${others.length ? `<p class="cause-more">Także: ${others.join(", ")}</p>` : ""}
      ${top.length ? `<h3 style="margin-top:12px">Co zrobić najpierw</h3><ol>${top.map((t) => `<li>${esc(t.title)}</li>`).join("")}</ol>` : ""}
    </div>
    ${stage(1, "Ocena sytuacji wodnej", r.assessment, "ocena")}
    ${stage(2, "Przyczyny", causesHtml(r.causes), "przyczyny")}
    ${stage(3, "Retencja: zatrzymaj wodę", r.retention, "retencja", true)}
    ${stage(4, "Agrotechnika: ogranicz straty", r.agrotechnics, "agrotechnika")}
    ${stage(5, "Nawadnianie: dopiero na końcu", r.irrigation, "nawadnianie", false, true)}
    <div class="card note"><b>Ograniczenia analizy</b><ul>${r.uncertainty.map((u) => `<li>${esc(u)}</li>`).join("")}</ul>
      <b>Źródła danych</b><ul>${r.data_sources.map((s) => `<li>${esc(s)}</li>`).join("")}</ul></div>`;
  $("result").hidden = false;
  $("result").querySelectorAll("button[data-lat]").forEach((b) =>
    b.addEventListener("click", () => {
      map.setView([+b.dataset.lat, +b.dataset.lon], 17);
      if (window.innerWidth <= 820) window.scrollTo({ top: 0, behavior: "smooth" });
    }));
}

const COLORS = { retencja: "#1d5f9a", ocena: "#e8b13a", agrotechnika: "#2e7d4f" };
function addMarker(it, group) {
  L.circleMarker([it.location.lat, it.location.lon], {
    radius: 9, color: "#fff", weight: 2, fillColor: COLORS[group] || "#555", fillOpacity: 1,
  }).bindPopup(`<b>${esc(it.title)}</b><br>${esc(it.detail)}`).addTo(markers);
}

// --- start --------------------------------------------------------------------
(async function init() {
  $("date").value = new Date().toISOString().slice(0, 10);
  try {
    const cs = await api("/crops");
    $("crop").innerHTML = cs.map((c) => `<option value="${c.key}">${esc(c.name)}</option>`).join("");
  } catch { showError("Serwer nie odpowiada. Uruchom: .venv/bin/uvicorn api.main:app"); }
})();
