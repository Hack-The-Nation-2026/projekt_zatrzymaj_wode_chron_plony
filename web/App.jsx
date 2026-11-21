import React, { useState, useRef, useEffect } from "react";
import "./styles.css";


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

// --- DUMMY API ---
const dummyApi = {
  searchParcelById: async (id) => ({
    id: id || "141201_1.0001.123/4",
    commune: "Tomaszów Mazowiecki",
    region: "Łazisko 352",
    area_ha: 3.01,
    center: { lat: 52.2297, lon: 21.0122 },
  }),
  resolveParcelByCoords: async (lat, lon) => ({
    id: "101609_2.0011.352",
    commune: "Tomaszów Mazowiecki",
    region: `Działka (${lat}, ${lon})`,
    area_ha: 3.01,
    center: { lat: Number(lat) || 52.2297, lon: Number(lon) || 21.0122 },
  }),
  runAnalysis: async ({ parcel, crop }) => ({
    id: "a1b2c3d4",
    parcel,
    crop,
    date: new Date().toISOString().slice(0, 10),
    risk_level: "Umiarkowane",
    risk_summary: "Zapas wody w strefie korzeniowej kurczy się (wyczerpanie 69,0 mm przy progu stresu RAW 58,0 mm). Warto wdrożyć działania retencyjne.",
    confidence: "średnia",
    main_cause: "Gleba słabo magazynuje wodę (lekka, piaszczysta – TAW 106,0 mm)",
    secondary_cause: "Odpływ powierzchniowy po spadku terenu (3,2% ku północy)",
    recommendations: [
      { step: "1. Retencja", title: "Zatrzymaj wodę w miejscu odpływu", detail: "Północna krawędź działki: zastawka lub próg spowalniający w rowie.", confidence: "średnia" },
      { step: "2. Agrotechnika", title: "Międzyplon ścierniskowy i ograniczenie orki", detail: "Zwiększenie próchnicy i ograniczenie parowania wody z gleby.", confidence: "wysoka" },
      { step: "3. Nawadnianie (ostateczność)", title: "Tylko interwencyjnie w fazie krytycznej", detail: "Zgodnie ze ścieżką KOWR stosowane wyłącznie po wyczerpaniu metod retencyjnych.", confidence: "średnia" },
    ],
    raw: { kbw60_mm: "-127,0 mm", depletion_mm: "69,0 mm", taw_mm: "106,0 mm", percentile: "16% najuboższych w wodę lat (z 31 lat)" },
  }),
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

  const handleFindById = async () => {
    const p = await dummyApi.searchParcelById(parcelInput.trim() || "141201_1.0001.123/4");
    setSelectedParcel(p);
  };

  const handleFindByCoords = async () => {
    const p = await dummyApi.resolveParcelByCoords(latInput || "52.2297", lonInput || "21.0122");
    setSelectedParcel(p);
  };

  const handleConfirmCrop = async () => {
    if (!selectedParcel) return;
    const cropObj = CROPS.find((c) => c.key === selectedCropKey) || CROPS[0];
    setLoadingReport(true);
    setTimeout(async () => {
      const res = await dummyApi.runAnalysis({ parcel: selectedParcel, crop: cropObj });
      setReport(res);
      setLoadingReport(false);
    }, 450);
  };

  const handleReset = () => {
    setSelectedParcel(null);
    setReport(null);
    topRef.current?.scrollIntoView({ behavior: "smooth" });
  };


  //Pobieranie raportu
  const handleDownloadReport = () => {
    if (!report) return;

    const toAscii = (str = "") =>
      String(str)
        .replace(/ą/g, "a").replace(/Ą/g, "A")
        .replace(/ć/g, "c").replace(/Ć/g, "C")
        .replace(/ę/g, "e").replace(/Ę/g, "E")
        .replace(/ł/g, "l").replace(/Ł/g, "L")
        .replace(/ń/g, "n").replace(/Ń/g, "N")
        .replace(/ó/g, "o").replace(/Ó/g, "O")
        .replace(/ś/g, "s").replace(/Ś/g, "S")
        .replace(/ź/g, "z").replace(/Ź/g, "Z")
        .replace(/ż/g, "z").replace(/Ż/g, "Z")
        .replace(/[–—]/g, "-")
        .replace(/↳/g, "->")
        .replace(/[^\x20-\x7E]/g, "");

    const wrap = (text, max = 82) => {
      const words = toAscii(text).split(/\s+/);
      const out = [];
      let cur = "";
      for (const w of words) {
        if ((cur + " " + w).trim().length > max) {
          out.push(cur.trim());
          cur = w;
        } else {
          cur = (cur + " " + w).trim();
        }
      }
      if (cur) out.push(cur);
      return out;
    };

    const lines = [
      "RAPORT NIEDOBOROW - WODNIK",
      "----------------------------------------------------------------------------------",
      `Dzialka: ${toAscii(report.parcel.id)} (${toAscii(report.parcel.region)})`,
      `Uprawa (plon): ${toAscii(report.crop.name)}`,
      `Data sprawdzenia: ${toAscii(report.date)}`,
      `Ryzyko suszy: ${toAscii(report.risk_level)} (pewnosc: ${toAscii(report.confidence)})`,
      "",
      "OCENA SYTUACJI WODNEJ:",
      ...wrap(report.risk_summary),
      "",
      "GLOWNE PRZYCZYNY:",
      ...wrap(`- ${report.main_cause}`),
      ...wrap(`- ${report.secondary_cause}`),
      "",
      "BILANS WODNY (FAO-56 / ERA5):",
      ...wrap(`KBW (60 dni): ${report.raw.kbw60_mm} | Wyczerpanie: ${report.raw.depletion_mm} / TAW ${report.raw.taw_mm}`),
      ...wrap(`Tlo wieloletnie: ${report.raw.percentile}`),
      "",
      "ZALECENIA (SCIEZKA KOWR):",
      ...report.recommendations.flatMap((r) => [
        ...wrap(`${r.step}: ${r.title} [pewnosc: ${r.confidence}]`),
        ...wrap(`   ${r.detail}`),
      ]),
    ];

    const esc = (s) => s.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
    const stream = [
      "BT",
      "/F1 11 Tf",
      "15 TL",
      "48 790 Td",
      ...lines.map((line, i) => (i === 0 ? `(${esc(line)}) Tj` : `T* (${esc(line)}) Tj`)),
      "ET",
    ].join("\n");

    const objs = [
      "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
      "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
      "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
      "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
      `5 0 obj\n<< /Length ${stream.length} >>\nstream\n${stream}\nendstream\nendobj\n`,
    ];

    let pdf = "%PDF-1.4\n";
    const offsets = [0];
    for (const o of objs) {
      offsets.push(pdf.length);
      pdf += o;
    }
    const xrefPos = pdf.length;
    pdf += `xref\n0 ${objs.length + 1}\n0000000000 65535 f \n`;
    for (let i = 1; i < offsets.length; i++) {
      pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
    }
    pdf += `trailer\n<< /Size ${objs.length + 1} /Root 1 0 R >>\nstartxref\n${xrefPos}\n%%EOF`;

    const cropSlug = toAscii(report.crop.name).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    const checkDate = report.date || new Date().toISOString().slice(0, 10);

    const blob = new Blob([pdf], { type: "application/pdf" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `raport_${cropSlug}_${checkDate}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredCrops = CROPS.filter((c) => {
    const matchesCategory = activeCategory === "Wszystkie" || c.category === activeCategory;
    const matchesSearch = c.name.toLowerCase().includes(cropSearch.toLowerCase());
    return matchesCategory && matchesSearch;
  });


  
  const selectedCropObj = CROPS.find((c) => c.key === selectedCropKey);

  // VIEW
  return (
    <div ref={topRef}>
      <header className="topbar">
        <strong style={{ fontSize: 16, cursor: "pointer" }} onClick={handleReset}>
          Wodnik
        </strong>
        <button className="btn dark" style={{ height: 38, padding: "0 16px" }} onClick={handleReset}>
          Strona główna
        </button>
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
                  <div
                    onClick={() => {
                      setLatInput("51.5450");
                      setLonInput("19.9493");
                      handleFindByCoords();
                    }}
                    style={{
                      marginTop: 14,
                      padding: 18,
                      border: "1px dashed #2b6e3f",
                      borderRadius: 10,
                      background: "#f1f7f3",
                      textAlign: "center",
                      cursor: "pointer",
                      fontSize: 13,
                    }}
                  >
                    🗺️ <strong>Ortofotomapa GUGiK (dummy)</strong> — kliknij tutaj, aby pobrać działkę Łazisko 352 (51.5450, 19.9493)
                  </div>
                )}
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 20 }}>
                <button className="btn dark" onClick={handleFindByCoords}>
                  Użyj współrzędnych
                </button>
                <button className="btn" onClick={() => setShowMapPicker((v) => !v)}>
                  Wybierz na mapie
                </button>
              </div>
            </div>
          </div>

          <p style={{ textAlign: "center", color: "#777770", fontSize: 13, marginTop: 28 }}>
            Wystarczy jedna metoda — numer działki lub lokalizacja.
          </p>
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
              <p className="sub" style={{ marginBottom: 16 }}>
                Wskaż uprawę na swojej działce, aby dopasować analizę retencji wody.
              </p>

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
                  <p className="sub" style={{ marginBottom: 0 }}>
                    Pobieranie danych GUGiK ULDK/NMT, ERA5-Land oraz SoilGrids (dummy API)…
                  </p>
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
                    <p style={{ fontSize: 14, color: "#333", margin: "0 0 12px" }}>
                      {report.risk_summary}
                    </p>

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

                    <div style={{ marginTop: 14 }}>
                      {report.recommendations.map((rec, i) => (
                        <div key={i} className="step-card">
                          <div style={{ fontSize: 12, fontWeight: 700, color: "#2b6e3f" }}>{rec.step}</div>
                          <div style={{ fontSize: 14, fontWeight: 600 }}>{rec.title}</div>
                          <div style={{ fontSize: 13, color: "#555" }}>{rec.detail}</div>
                        </div>
                      ))}
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
                      <button className="btn" onClick={() => window.print()}>
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
