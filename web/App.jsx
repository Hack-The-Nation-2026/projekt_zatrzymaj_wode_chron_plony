import React, { useState, useRef, useEffect } from "react";
import { Document, Page, Text, View, StyleSheet, Font, pdf } from "@react-pdf/renderer";
import "./styles.css";
import { api } from "./api.js";
import Scenarios from "./Scenarios.jsx";

Font.register({
  family: "Roboto",
  fonts: [
    { src: "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-regular-webfont.ttf" },
    { src: "https://cdnjs.cloudflare.com/ajax/libs/ink/3.1.10/fonts/Roboto/roboto-bold-webfont.ttf", fontWeight: 700 },
  ],
});

const dedupeRecommendations = (recs = []) => {
  const seen = new Set();
  return recs.filter((r) => {
    const key = `${r.step}|${r.title}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

const groupRecommendations = (recs = []) => {
  const groups = [];
  for (const r of dedupeRecommendations(recs)) {
    let g = groups.find((x) => x.step === r.step);
    if (!g) {
      g = { step: r.step, items: [] };
      groups.push(g);
    }
    g.items.push(r);
  }
  return groups;
};

const s = StyleSheet.create({
  page: { padding: 36, fontFamily: "Roboto", fontSize: 10, color: "#1a2a1f" },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 14,
            borderBottomWidth: 2, borderBottomColor: "#4a9d3f", paddingBottom: 8 },
  title: { fontSize: 18, fontWeight: 700 },
  meta: { fontSize: 9, color: "#4a5a50", marginBottom: 12 },
  badge: { backgroundColor: "#fff3cd", color: "#8a6d00", padding: "4 10", borderRadius: 10, fontSize: 9, fontWeight: 700 },
  row: { flexDirection: "row", gap: 12, marginBottom: 12 },
  card: { flex: 1, borderWidth: 1, borderColor: "#d8e0da", borderRadius: 6, padding: 10 },
  cardLabel: { fontSize: 8, color: "#556", textTransform: "uppercase", marginBottom: 4, fontWeight: 700 },
  table: { borderWidth: 1, borderColor: "#d8e0da", borderRadius: 6, marginTop: 6 },
  trHead: { flexDirection: "row", backgroundColor: "#eef4ef", borderBottomWidth: 1, borderBottomColor: "#d8e0da", padding: "7 10" },
  tr: { flexDirection: "row", borderBottomWidth: 1, borderBottomColor: "#e6ece8", padding: "8 10" },
  thStep: { width: "24%", fontSize: 8, fontWeight: 700, color: "#2d4a34", textTransform: "uppercase" },
  thAction: { width: "76%", fontSize: 8, fontWeight: 700, color: "#2d4a34", textTransform: "uppercase" },
  tdStep: { width: "24%", fontSize: 9, fontWeight: 700, color: "#2b6e3f", paddingRight: 8 },
  tdAction: { width: "76%", fontSize: 9 },
  itemBlock: { marginBottom: 6 },
});

const ReportPdf = ({ report }) => {
  const grouped = groupRecommendations(report.recommendations);
  return (
    <Document>
      <Page size="A4" style={s.page}>
        <View style={s.header}>
          <Text style={s.title}>Raport niedoborów – Wodnik</Text>
          <Text style={s.badge}>Ryzyko suszy: {report.risk_level}</Text>
        </View>
        <Text style={s.meta}>
          Działka: {report.parcel?.id} ({report.parcel?.region})  |  Uprawa: {report.crop?.name}  |  Data analizy: {report.date}
        </Text>
        <View style={s.row}>
          <View style={s.card}>
            <Text style={s.cardLabel}>Główne przyczyny</Text>
            <Text>{report.main_cause}</Text>
            <Text style={{ marginTop: 3, color: "#445" }}>{report.secondary_cause}</Text>
          </View>
          <View style={s.card}>
            <Text style={s.cardLabel}>Bilans wodny (FAO-56 / ERA5)</Text>
            <Text>KBW (60 dni): {report.raw.kbw60_mm}</Text>
            <Text>Wyczerpanie: {report.raw.depletion_mm} / TAW {report.raw.taw_mm}</Text>
            <Text style={{ marginTop: 3, color: "#445" }}>{report.raw.percentile}</Text>
          </View>
        </View>
        {report.scenarios && (
          <View style={[s.card, { marginBottom: 12 }]}>
            <Text style={s.cardLabel}>Co dalej: najbliższe {report.scenarios.horizon_days} dni ({report.scenarios.years} scenariuszy)</Text>
            <Text>{report.scenarios.summary}</Text>
            <Text style={{ marginTop: 3 }}>
              Woda potrzebna, by uniknąć stresu: ok. {report.scenarios.water_needed_p50_mm} mm (suchy scenariusz: {report.scenarios.water_needed_p90_mm} mm)
            </Text>
          </View>
        )}
        <View style={s.table}>
          <View style={s.trHead}>
            <Text style={s.thStep}>Etap KOWR</Text>
            <Text style={s.thAction}>Zalecane działania i uzasadnienie</Text>
          </View>
          {grouped.map((g, gi) => (
            <View key={g.step} style={[s.tr, gi === grouped.length - 1 && { borderBottomWidth: 0 }]} wrap={false}>
              <Text style={s.tdStep}>{g.step}</Text>
              <View style={s.tdAction}>
                {g.items.map((it, ii) => (
                  <View key={ii} style={ii < g.items.length - 1 ? s.itemBlock : null}>
                    <Text style={{ fontWeight: 700 }}>{it.title}</Text>
                    <Text style={{ color: "#334", marginTop: 1 }}>{it.detail}</Text>
                  </View>
                ))}
              </View>
            </View>
          ))}
        </View>
      </Page>
    </Document>
  );
};


// --- LISTA UPRAW (jako klocki z kategoriami jak na screenie 2) ---
const CROPS = [
  { key: "pszenica_ozima", name: "Pszenica ozima", category: "Zboża" },
  { key: "pszenica_jara", name: "Pszenica jara", category: "Zboża" },
  { key: "kukurydza", name: "Kukurydza", category: "Zboża" },
  { key: "jeczmien_jary", name: "Jęczmień jary", category: "Zboża" },
  { key: "zyto", name: "Żyto", category: "Zboża" },
  { key: "rzepak_ozimy", name: "Rzepak ozimy", category: "Oleiste" },
  { key: "burak_cukrowy", name: "Burak cukrowy", category: "Okopowe" },
  { key: "ziemniaki", name: "Ziemniak", category: "Okopowe" },
  { key: "uzytki_zielone", name: "Trwałe użytki zielone", category: "Inne" },
];




const CATEGORIES = ["Wszystkie", "Zboża", "Oleiste", "Okopowe", "Inne"];

// Dane pochodzą z serwera Wodnika (web/api.js → FastAPI → analiza w wodnik/).
// Działka demo z gotowym wynikiem (działa bez internetu): 101609_2.0011.352, data 2026-06-15, pszenica ozima.
const DEMO = { id: "101609_2.0011.352", date: "2026-06-15", lat: "51.5450", lon: "19.9493" };

function ParcelMap({ parcel, initialCenter, onPickPoint }) {
  const mapElRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const parcelLayerRef = useRef(null);

  useEffect(() => {
    const L = window.L;
    if (!L || !mapElRef.current || mapInstanceRef.current) return;

    const map = L.map(mapElRef.current, { zoomControl: true }).setView(initialCenter || [51.545, 19.9493], 15);
    const osm = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    });
    const orto = L.tileLayer.wms("https://mapy.geoportal.gov.pl/wss/service/PZGIK/ORTO/WMS/StandardResolution", {
      layers: "Raster",
      format: "image/jpeg",
      maxZoom: 19,
      attribution: "Ortofotomapa © GUGiK",
    });
    const parcels = L.tileLayer.wms("https://integracja.gugik.gov.pl/cgi-bin/KrajowaIntegracjaEwidencjiGruntow", {
      layers: "dzialki,numery_dzialek",
      format: "image/png",
      transparent: true,
      minZoom: 15,
      maxZoom: 19,
      attribution: "Działki © GUGiK",
    });

    orto.addTo(map);
    parcels.addTo(map);
    L.control.layers({ "Zdjęcie lotnicze": orto, "Mapa": osm }, { "Granice działek": parcels }).addTo(map);

    map.on("click", (e) => {
      onPickPoint(e.latlng.lat.toFixed(6), e.latlng.lng.toFixed(6));
    });

    mapInstanceRef.current = map;
    setTimeout(() => map.invalidateSize(), 100);

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      parcelLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const L = window.L;
    const map = mapInstanceRef.current;
    if (!L || !map) return;

    if (parcelLayerRef.current) {
      map.removeLayer(parcelLayerRef.current);
      parcelLayerRef.current = null;
    }

    if (parcel?.geometry) {
      const layer = L.geoJSON(parcel.geometry, {
        style: { color: "#e8b13a", weight: 3, fillOpacity: 0.15 },
      }).addTo(map);
      parcelLayerRef.current = layer;
      map.fitBounds(layer.getBounds(), { maxZoom: 17, padding: [24, 24] });
    }
  }, [parcel]);

  return (
    <div style={{ marginTop: 14 }}>
      <div
        ref={mapElRef}
        style={{
          height: 300,
          width: "100%",
          borderRadius: 10,
          border: "1px solid #2c465d",
          overflow: "hidden",
        }}
      />
      <div style={{ fontSize: 12, color: "#9db0c0", marginTop: 6 }}>
        Dotknij dowolnego pola na mapie, aby pobrać granice działki z GUGiK ULDK.
      </div>
    </div>
  );
}

// RESET
// Pełny reset: czyści też pola formularza, wybraną uprawę i datę
const handleRestart = () => {
  setParcelInput("");
  setLatInput("");
  setLonInput("");
  setShowMapPicker(false);
  setSelectedParcel(null);
  setCropSearch("");
  setActiveCategory("Wszystkie");
  setSelectedCropKey("pszenica_ozima");
  setAnalysisDate(new Date().toISOString().slice(0, 10));
  setReport(null);
  setProgress([]);
  setError("");
  setLoadingReport(false);
  topRef.current?.scrollIntoView({ behavior: "smooth" });
};


export default function App() {
  // Stan kroku 1: Działka
  const [parcelInput, setParcelInput] = useState("");
  const [latInput, setLatInput] = useState("");
  const [lonInput, setLonInput] = useState("");
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [selectedParcel, setSelectedParcel] = useState(null);

  // Stan kroku 2: Uprawa (klocki)
  const [cropSearch, setCropSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("Wszystkie");
  const [selectedCropKey, setSelectedCropKey] = useState("pszenica_ozima");

  // Stan kroku 3: Raport
  const [loadingReport, setLoadingReport] = useState(false);
  const [report, setReport] = useState(null);
  const [analysisDate, setAnalysisDate] = useState(new Date().toISOString().slice(0, 10));
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState("");

  // Referencje do płynnego scrollowania w dół
  const topRef = useRef(null);
  const cropSectionRef = useRef(null);
  const reportSectionRef = useRef(null);

  // Automatyczny scroll po wyborze działki -> do sekcji wyboru plonów
  useEffect(() => {
    if (selectedParcel && cropSectionRef.current) {
      cropSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [selectedParcel]);

  // Automatyczny scroll po wygenerowaniu raportu -> do sekcji raportu
  useEffect(() => {
    if ((loadingReport || report) && reportSectionRef.current) {
      reportSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [loadingReport, report]);

  const pickParcel = async (load) => {
    setError("");
    setReport(null);
    try {
      setSelectedParcel(await load());
    } catch (e) {
      setError(e.message);
    }
  };

  const handleFindById = () => {
    const id = parcelInput.trim();
    if (!id) return setError("Wpisz identyfikator działki, np. " + DEMO.id);
    pickParcel(() => api.searchParcelById(id));
  };

  const handleFindByCoords = (lat = latInput, lon = lonInput) => {
    if (!lat || !lon) return setError("Podaj obie współrzędne albo wybierz działkę na mapie.");
    pickParcel(() => api.resolveParcelByCoords(lat, lon));
  };

  const handleDemo = () => {
    setParcelInput(DEMO.id);
    setAnalysisDate(DEMO.date);
    setSelectedCropKey("pszenica_ozima");
    pickParcel(() => api.searchParcelById(DEMO.id));
  };

  const handleConfirmCrop = async () => {
    if (!selectedParcel) return;
    const cropObj = CROPS.find((c) => c.key === selectedCropKey) || CROPS[0];
    setError("");
    setReport(null);
    setProgress([]);
    setLoadingReport(true);
    try {
      setReport(await api.runAnalysis({ parcel: selectedParcel, crop: cropObj, date: analysisDate, onProgress: setProgress }));
    } catch (e) {
      setError(e.message);
    } finally {
      setLoadingReport(false);
    }
  };

  const handleReset = () => {
    setSelectedParcel(null);
    setReport(null);
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  };


  //Pobieranie raportu
  const handleDownloadReport = async () => {
    if (!report) return;
    try {
      const cropSlug = report.crop.key || report.crop.name.toLowerCase().replace(/\s+/g, "_");
      const checkDate = report.date || new Date().toISOString().slice(0, 10);
      const blob = await pdf(<ReportPdf report={report} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `raport_${cropSlug}_${checkDate}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch (e) {
      setError("Nie udało się wygenerować PDF: " + e.message);
    }
  };

  const filteredCrops = CROPS.filter((c) => {
    const matchesCategory = activeCategory === "Wszystkie" || c.category === activeCategory;
    const matchesSearch = c.name.toLowerCase().includes(cropSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Drukowanie raportu jako PDF
  const handlePrintReport = async () => {
    if (!report) return;
    try {
      const blob = await pdf(<ReportPdf report={report} />).toBlob();
      const url = URL.createObjectURL(blob);
      const win = window.open(url, "_blank");
      if (!win) {
        window.print();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) {
      window.print();
    }
  };


  const selectedCropObj = CROPS.find((c) => c.key === selectedCropKey);

  // VIEW
  return (
    <div ref={topRef}>
      <header className="topbar">
  <strong style={{ fontSize: 16, cursor: "pointer" }} onClick={handleReset}>
    Wodnik
  </strong>
  <div className="topbar-actions">
    <button
      className="btn dark icon-btn"
      onClick={handleReset}
      aria-label="Strona główna"
      title="Strona główna"
    >
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5 10v10h5v-6h4v6h5V10" />
      </svg>
    </button>
    <button
      className="btn dark"
      style={{ height: 38, padding: "0 16px" }}
      onClick={handleRestart}
    >
      Od nowa
    </button>
  </div>
</header>

      <main className="container">
        {/* KROK 1: WYBÓR DZIAŁKI (widoczny od razu na starcie) */}
        <section className="section">
          <div className="eyebrow">RETENCJA WODY W ROLNICTWIE</div>
          <h1>Sprawdź możliwości retencji na swojej działce</h1>
          <p className="sub">Wpisz numer ewidencyjny działki lub wybierz jej lokalizację, aby rozpocząć.</p>

          <div className="grid-2">
            {/* Karta lewa: Numer ewidencyjny działki */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <h2>Numer ewidencyjny działki</h2>
                <p className="sub" style={{ marginBottom: 16 }}>Znajdź działkę na podstawie jej identyfikatora.</p>
                <label>Identyfikator działki</label>
                <input
                  placeholder="np. 141201_1.0001.123/4"
                  value={parcelInput}
                  onChange={(e) => setParcelInput(e.target.value)}
                />
              </div>
              <button className="btn dark" style={{ width: "100%", marginTop: 20 }} onClick={handleFindById}>
                Znajdź działkę
              </button>
            </div>

            {/* Karta prawa: Lokalizacja geograficzna */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <h2>Lokalizacja geograficzna</h2>
                <p className="sub" style={{ marginBottom: 16 }}>Podaj współrzędne lub wskaż działkę na mapie.</p>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  <div>
                    <label>Szerokość geograficzna</label>
                    <input
                      placeholder="np. 52.2297"
                      value={latInput}
                      onChange={(e) => setLatInput(e.target.value)}
                    />
                  </div>
                  <div>
                    <label>Długość geograficzna</label>
                    <input
                      placeholder="np. 21.0122"
                      value={lonInput}
                      onChange={(e) => setLonInput(e.target.value)}
                    />
                  </div>
                </div>

                {showMapPicker && (
                  <ParcelMap
                    parcel={selectedParcel}
                    initialCenter={[
                      Number(latInput) || Number(DEMO.lat),
                      Number(lonInput) || Number(DEMO.lon),
                    ]}
                    onPickPoint={(lat, lon) => {
                      setLatInput(lat);
                      setLonInput(lon);
                      handleFindByCoords(lat, lon);
                    }}
                  />
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 20 }}>
                <button className="btn dark" onClick={() => handleFindByCoords()}>
                  Użyj współrzędnych
                </button>
                <button className="btn" onClick={() => setShowMapPicker((v) => !v)}>
                  Wybierz na mapie
                </button>
              </div>
            </div>
          </div>

          <p style={{ textAlign: "center", color: "#777770", fontSize: 13, marginTop: 28 }}>
            Wystarczy jedna metoda — numer działki lub lokalizacja.{" "}
            <span style={{ color: "#63b34e", cursor: "pointer", textDecoration: "underline" }} onClick={handleDemo}>
              Wypróbuj na przykładzie (Łazisko, 15.06.2026)
            </span>
          </p>
          {error && !selectedParcel && <p className="error-msg" role="alert">{error}</p>}
        </section>

        {/* KROK 2: WYBÓR UPRAWY JAKO KLOCKI (pojawia się i scrolluje w dół po wyborze działki) */}
        {selectedParcel && (
          <section ref={cropSectionRef} className="section">
            <div className="panel" style={{ maxWidth: 680, margin: "0 auto", width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2>Wybierz uprawę</h2>
                <span
                  style={{ fontSize: 13, color: "#666", cursor: "pointer" }}
                  onClick={() => topRef.current?.scrollIntoView({ behavior: "smooth" })}
                >
                  Zmień działkę ({selectedParcel.id})
                </span>
              </div>

              <label>Szukaj uprawy</label>
              <input
                placeholder="Wpisz nazwę uprawy"
                value={cropSearch}
                onChange={(e) => setCropSearch(e.target.value)}
              />

              {/* Kategorie filtrujące */}
              <div className="pills">
                {CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    className={`pill ${activeCategory === cat ? "active" : ""}`}
                    onClick={() => setActiveCategory(cat)}
                  >
                    {cat}
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, fontWeight: 600, color: "#555", marginBottom: 10 }}>
                <span>Popularne uprawy</span>
                <span style={{ fontWeight: 400 }}>Wybierz jedną</span>
              </div>

              {/* Siatka klocków upraw */}
              <div className="crop-grid">
                {filteredCrops.map((c) => {
                  const isSelected = c.key === selectedCropKey;
                  return (
                    <button
                      key={c.key}
                      type="button"
                      className={`crop-tile ${isSelected ? "selected" : ""}`}
                      onClick={() => setSelectedCropKey(c.key)}
                    >
                      <span className="radio" />
                      <div>
                        <div style={{ fontWeight: 600, fontSize: 14, color: "#141413" }}>{c.name}</div>
                        <div style={{ fontSize: 12, color: "#777770" }}>{c.category}</div>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Data analizy – wymóg zadania: analiza dla wskazanej działki i daty */}
              <label>Data analizy</label>
              <input type="date" value={analysisDate} max={new Date(Date.now() + 7 * 864e5).toISOString().slice(0, 10)}
                     onChange={(e) => setAnalysisDate(e.target.value)} />
              {error && selectedParcel && <p className="error-msg" role="alert">{error}</p>}

              {/* Stopka wyboru uprawy */}
              <div className="panel-footer">
                <div style={{ fontSize: 13, color: "#555" }}>
                  Wybrana uprawa: <strong style={{ color: "#141413" }}>{selectedCropObj?.name}</strong>
                </div>
                <div style={{ display: "flex", gap: 10 }}>
                  <button
                    className="btn"
                    onClick={() => topRef.current?.scrollIntoView({ behavior: "smooth" })}
                  >
                    Anuluj
                  </button>
                  <button className="btn dark" onClick={handleConfirmCrop}>
                    Zatwierdź wybór
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* KROK 3: RAPORT NIEDOBORÓW (pojawia się i scrolluje w dół po zatwierdzeniu uprawy) */}
        {(loadingReport || report) && (
          <section ref={reportSectionRef} className="section">
            <div className="panel">
              {loadingReport ? (
                <div style={{ padding: "24px 0", textAlign: "center" }}>
                  <h2>Generowanie raportu niedoborów…</h2>
                  <p className="sub" style={{ marginBottom: 12 }}>
                    Pobieranie danych GUGiK, ERA5, SoilGrids i Sentinel-2. Pierwsza analiza działki trwa do ok. minuty.
                  </p>
                  <ul className="progress-list">
                    {progress.map((s) => (
                      <li key={s.step} className={s.state}>{s.label}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                    <h2>Raport niedoborów</h2>
                    <span
                      style={{ fontSize: 13, color: "#555", cursor: "pointer", fontWeight: 600 }}
                      onClick={handleDownloadReport}
                    >
                      Pobierz
                    </span>
                  </div>

                  <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
                      Stan niedoboru{" "}
                      <span className="badge warn" style={{ marginLeft: 8 }}>
                        Ryzyko suszy: {report.risk_level} (pewność: {report.confidence})
                      </span>
                    </div>
                    <div
                      style={{
                        backgroundColor: "#ffffff",
                        color: "#141413",
                        padding: "14px 18px",
                        borderRadius: "12px",
                        margin: "0 0 16px",
                        fontSize: 14,
                        lineHeight: 1.5,
                        boxShadow: "0 2px 8px rgba(0, 0, 0, 0.18)",
                      }}
                    >
                      <strong>Podsumowanie ryzyka:</strong> {report.risk_summary}
                    </div>

                    {/* Zwięzłe podsumowanie danych i ścieżki KOWR */}
                    <div className="grid-2" style={{ marginTop: 16 }}>
                      <div className="step-card">
                        <div style={{ fontSize: 12, fontWeight: 700, color: "#555" }}>GŁÓWNE PRZYCZYNY NA DZIAŁCE</div>
                        <div style={{ fontSize: 14, fontWeight: 600, marginTop: 4 }}>{report.main_cause}</div>
                        <div style={{ fontSize: 13, color: "#555", marginTop: 4 }}>↳ {report.secondary_cause}</div>
                      </div>
                      <div className="step-card">
                        <div style={{ fontSize: 12, fontWeight: 700, color: "#555" }}>BILANS WODNY (FAO-56 / ERA5)</div>
                        <div style={{ fontSize: 13, marginTop: 4 }}>
                          KBW (60 dni): <strong>{report.raw.kbw60_mm}</strong> · Wyczerpanie: <strong>{report.raw.depletion_mm}</strong> / TAW {report.raw.taw_mm}
                        </div>
                        <div style={{ fontSize: 12, color: "#666", marginTop: 4 }}>
                          Tło wieloletnie: {report.raw.percentile}
                        </div>
                      </div>
                    </div>

                    <Scenarios s={report.scenarios} />

                    <div className="rec-table-wrap">
                      <table className="rec-table">
                        <thead>
                          <tr>
                            <th>Etap ścieżki KOWR</th>
                            <th>Zalecane działania na działce</th>
                            <th>Pewność</th>
                          </tr>
                        </thead>
                        <tbody>
                          {groupRecommendations(report.recommendations).map((group) =>
                            group.items.map((rec, idx) => (
                              <tr key={`${group.step}-${idx}`} className={idx === 0 ? "rec-group-start" : ""}>
                                {idx === 0 && (
                                  <td className="rec-cat" rowSpan={group.items.length}>
                                    {group.step}
                                  </td>
                                )}
                                <td>
                                  <div className="rec-item">
                                    <div className="rec-title">{rec.title}</div>
                                    <div className="rec-detail">{rec.detail}</div>
                                  </div>
                                </td>
                                <td className="rec-conf">
                                  <span className="badge">{rec.confidence || "średnia"}</span>
                                </td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* Stopka raportu identyczna jak na screenie 3 */}
                  <div className="panel-footer">
                    <div style={{ fontSize: 13, color: "#555" }}>
                      Wybrana uprawa: <strong style={{ color: "#141413" }}>{report.crop.name}</strong>
                      <span style={{ marginLeft: 12, color: "#888" }}>
                        (Działka: {report.parcel.id})
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 10 }}>
                      <button className="btn" onClick={handlePrintReport}>
                        Drukuj
                      </button>
                      <button className="btn dark" onClick={handleDownloadReport}>
                        Pobierz
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
