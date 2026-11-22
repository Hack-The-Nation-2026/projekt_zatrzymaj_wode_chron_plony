import React, { useState, useRef, useEffect } from "react";
import "./styles.css";
import { useFontSize } from "./useFontSize.js";
import { api } from "./api.js";
import Scenarios from "./Scenarios.jsx";
import { HistoryChart, YearsChart } from "./Charts.jsx";
import Chat from "./Chat.jsx";
import WhatIf from "./WhatIf.jsx";
import Landing from "./Landing.jsx";
import Profile from "./Profile.jsx";

const groupRecommendations = (recs = []) => {
  const groups = [];
  const seen = new Set();
  for (const r of recs) {
    const key = `${r.step}|${r.title}`;
    if (seen.has(key)) continue;
    seen.add(key);
    let g = groups.find((x) => x.step === r.step);
    if (!g) {
      g = { step: r.step, items: [] };
      groups.push(g);
    }
    g.items.push(r);
  }
  return groups;
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

export default function App() {
  const [fontSize, setFontSize] = useFontSize();
  // Konto: strona startowa z logowaniem, aplikacja, profil z historią raportów
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [guest, setGuest] = useState(false);
  const [view, setView] = useState("app"); // "app" | "profile"

  useEffect(() => {
    api.me().then((u) => setUser(u)).finally(() => setAuthChecked(true));
  }, []);

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
    setView("app");
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setGuest(false);
    setView("app");
    setReport(null);
    setSelectedParcel(null);
    window.scrollTo({ top: 0 });
  };

  // Raport otwarty z historii w profilu
  const handleOpenReport = (r) => {
    setError("");
    setSelectedParcel(r.parcel);
    setReport(r);
    setView("app");
  };

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
    setView("app");
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  };


  const filteredCrops = CROPS.filter((c) => {
    const matchesCategory = activeCategory === "Wszystkie" || c.category === activeCategory;
    const matchesSearch = c.name.toLowerCase().includes(cropSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  // Drukowanie (otwiera widok do druku w nowej karcie) oraz pobieranie (pobiera gotowy plik PDF)
  const handlePrintReport = async () => {
    if (!report) return;
    setError("");
    try {
      await (report.historyId
        ? api.openReportHtml(report.historyId)
        : api.openAnalysisHtml(report.id));
    } catch (e) {
      setError(e.message);
    }
  };

  const handleDownloadReport = async () => {
    if (!report) return;
    setError("");
    const fallbackName = `raport_${report.parcel?.id || "dzialka"}_${report.date || ""}.pdf`;
    try {
      await (report.historyId
        ? api.downloadReportPdf(report.historyId, fallbackName)
        : api.downloadAnalysisPdf(report.id, fallbackName));
    } catch (e) {
      setError(e.message);
    }
  };


  const selectedCropObj = CROPS.find((c) => c.key === selectedCropKey);

  // VIEW
  if (!authChecked) return null;
  if (!user && !guest) {
    return (
      <Landing
        onAuth={(u) => { setUser(u); setView("app"); window.scrollTo({ top: 0 }); }}
        onGuest={() => { setGuest(true); window.scrollTo({ top: 0 }); }}
      />
    );
  }

  return (
    <div ref={topRef}>
      <header className="topbar">
  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
    <strong style={{ fontSize: 16, cursor: "pointer" }} onClick={handleReset}>
      Wodnik
    </strong>
    <div className="font-size-picker" role="group" aria-label="Wielkość czcionki">
      <button type="button" className={`font-size-btn ${fontSize === "sm" ? "active" : ""}`} onClick={() => setFontSize("sm")} title="Mała czcionka">
        <span style={{ fontSize: "11px", lineHeight: 1 }}>A</span>
      </button>
      <button type="button" className={`font-size-btn ${fontSize === "md" ? "active" : ""}`} onClick={() => setFontSize("md")} title="Średnia czcionka">
        <span style={{ fontSize: "14px", lineHeight: 1 }}>A</span>
      </button>
      <button type="button" className={`font-size-btn ${fontSize === "lg" ? "active" : ""}`} onClick={() => setFontSize("lg")} title="Duża czcionka">
        <span style={{ fontSize: "18px", lineHeight: 1 }}>A</span>
      </button>
    </div>
  </div>
  <div className="topbar-actions">
    <button
      className="btn dark"
      style={{ height: 38, padding: "0 16px" }}
      onClick={handleRestart}
    >
      Od nowa
    </button>
    {user ? (
      <>
        <button className="btn" style={{ height: 38, padding: "0 16px" }} onClick={() => setView("profile")}
                title={user.email}>
          Twoje raporty
        </button>
        <button className="btn" style={{ height: 38, padding: "0 16px" }} onClick={handleLogout}>Wyloguj</button>
      </>
    ) : (
      <button className="btn" style={{ height: 38, padding: "0 16px" }} onClick={() => setGuest(false)}>
        Zaloguj się
      </button>
    )}
  </div>
</header>

      {view === "profile" && user ? (
        <Profile user={user} onOpenReport={handleOpenReport} onBack={handleRestart} />
      ) : (

      <main className="container">
        {/* Pasek kroków: gdzie jestem w analizie */}
        <ol className="stepper" aria-label="Kroki analizy">
          <li className={selectedParcel ? "done" : "on"}><span>1</span>Twoje pole</li>
          <li className={report ? "done" : selectedParcel ? "on" : ""}><span>2</span>Uprawa i data</li>
          <li className={report ? "on" : ""}><span>3</span>Raport i rady</li>
        </ol>

        {/* KROK 1: WYBÓR DZIAŁKI (widoczny od razu na starcie) */}
        <section className="section">
          <div className="eyebrow">{user?.name ? `Dzień dobry, ${user.name}` : "Krok 1 · Twoje pole"}</div>
          <h1>Gdzie jest Twoje pole?</h1>
          <p className="sub">
            Wpisz numer działki z ewidencji albo wskaż pole na mapie. Resztę sprawdzimy za Ciebie: pogodę z ostatnich
            10 lat, glebę, ukształtowanie terenu, rowy w okolicy i stan roślin ze zdjęć satelitarnych.
          </p>

          <div className="grid-2">
            {/* Karta lewa: Numer ewidencyjny działki */}
            <div className="panel" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
              <div>
                <h2>Mam numer działki</h2>
                <p className="sub" style={{ marginBottom: 16 }}>Znajdziesz go w wypisie z ewidencji albo we wniosku o dopłaty.</p>
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
                <h2>Pokażę na mapie</h2>
                <p className="sub" style={{ marginBottom: 16 }}>Kliknij swoje pole na zdjęciu lotniczym albo wpisz współrzędne.</p>
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
            Nie masz pod ręką numeru?{" "}
            <span style={{ color: "#63b34e", cursor: "pointer", textDecoration: "underline" }} onClick={handleDemo}>
              Zobacz przykładowe pole w Łazisku (pszenica, 15.06.2026)
            </span>
          </p>
          {error && !selectedParcel && <p className="error-msg" role="alert">{error}</p>}
        </section>

        {/* KROK 2: WYBÓR UPRAWY JAKO KLOCKI (pojawia się i scrolluje w dół po wyborze działki) */}
        {selectedParcel && (
          <section ref={cropSectionRef} className="section">
            <div className="panel" style={{ maxWidth: 680, margin: "0 auto", width: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h2>Co rośnie na tym polu?</h2>
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
                <div style={{ padding: "12px 0 24px", textAlign: "center" }}>
                  <img className="loader-gif" src="/img/klos-ladowanie.gif" alt="" aria-hidden="true" width="380" height="252" />
                  <h2>Sprawdzamy Twoje pole…</h2>
                  <p className="sub" style={{ marginBottom: 12 }}>
                    Zbieramy dane o pogodzie, glebie, terenie i roślinach z kilku publicznych źródeł naraz.
                    Nowe pole liczy się zwykle do minuty, a pole sprawdzane wcześniej od razu.
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
                    <h2>Twój raport</h2>
                  </div>

                  <div style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
                      Stan niedoboru{" "}
                      <span className={`badge ${{ niskie: "ok", umiarkowane: "warn", wysokie: "bad" }[String(report.risk_level).toLowerCase()] || "warn"}`}
                            style={{ marginLeft: 8 }}>
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
                      <strong>W skrócie:</strong> {report.risk_summary}
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
                        <YearsChart charts={report.charts} />
                      </div>
                    </div>

                    <HistoryChart charts={report.charts} scenarios={report.scenarios} />
                    <Scenarios s={report.scenarios} />
                    <WhatIf w={report.whatIf} />

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

                    <Chat report={report} />
                  </div>
                  {error && <p className="error-msg" role="alert" style={{ marginBottom: 16 }}>{error}</p>}

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
      )}
      <footer className="app-foot">
        Wodnik powstał na HackNation 2026, żeby pomagać rolnikom zatrzymać wodę na polu. Rady opieramy na publicznych
        danych i jawnych metodach; ważne decyzje warto omówić z doradcą rolniczym (ODR).
      </footer>
    </div>
  );
}
