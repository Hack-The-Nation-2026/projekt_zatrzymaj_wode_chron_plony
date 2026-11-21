# Architektura i struktura projektu

Dokument opisuje, jak jest zbudowany Wodnik dziś (prototyp danych w Pythonie) i jak ma wyglądać po dołożeniu serwera, interfejsu i raportów AI. Elementy oznaczone **[plan]** jeszcze nie istnieją.

## Zasady projektowe

1. **Rekomendacje liczy kod, nie model językowy.** Reguły naukowe (FAO-56, pedotransfer, analiza terenu) są jawne i testowalne. AI tylko tłumaczy gotowy wynik na prosty język (patrz [RAPORT_AI.md](RAPORT_AI.md)).
2. **Kolejność KOWR jest sztywna:** ocena sytuacji wodnej → przyczyny → retencja → agrotechnika → nawadnianie (na końcu).
3. **Każdy wniosek ma uzasadnienie i pewność.** Struktura `Item` (`title`, `detail`, `because`, `confidence`) jest jedynym formatem rekomendacji w całym systemie.
4. **Tylko dane publiczne i otwarte licencje**, bo kod przechodzi na KOWR.
5. **Demo nie zależy od sieci:** odpowiedzi zewnętrznych API są cache'owane na dysku (`WODNIK_OFFLINE=1`).

## Widok ogólny

```
 Przeglądarka (telefon / komputer)
 ┌──────────────────────────────────────────────┐
 │  web/  – mapa (Leaflet), formularz, wyniki   │
 └───────────────────┬──────────────────────────┘
                     │ JSON przez HTTPS  (patrz API.md)
 ┌───────────────────▼──────────────────────────┐
 │  api/  – FastAPI                             │
 │   • walidacja wejścia, zadania, cache wyników│
 │   • wywołuje wodnik.analysis.analyse()       │
 │   • wywołuje wodnik.ai_report  (opcjonalnie) │
 └───────┬───────────────────────────┬──────────┘
         │                           │
 ┌───────▼─────────────┐     ┌───────▼──────────┐
 │ wodnik/ (rdzeń)     │     │ Claude API       │
 │  dane + analiza     │     │ (raport AI) [plan]│
 └───────┬─────────────┘     └──────────────────┘
         │ HTTP + cache na dysku
 ┌───────▼───────────────────────────────────────┐
 │ ULDK · NMT/WCS (GUGiK) · Open-Meteo/ERA5      │
 │ SoilGrids · [plan] Sentinel-2 · BDOT10k       │
 └───────────────────────────────────────────────┘
```

## Struktura katalogów

```
projekt_zatrzymaj_wode_chron_plony/
├── README.md               uruchomienie, dane, licencje, ograniczenia
├── requirements.txt
├── docs/
│   ├── ARCHITEKTURA.md     ten plik
│   ├── UI.md               strony i makiety
│   ├── API.md              zapytania do serwera
│   └── RAPORT_AI.md        raport AI, prompt, zabezpieczenia
├── wodnik/                 RDZEŃ (działa)
│   ├── __main__.py         wiersz poleceń: python -m wodnik
│   ├── analysis.py         5 kroków KOWR, reguły, progi, niepewność
│   ├── parcel.py           działka z ULDK (po ID lub punkcie)
│   ├── weather.py          opad, ET0, wilgotność gleby, tło 10 lat przed datą
│   ├── waterbalance.py     bilans FAO-56 (TAW, RAW, Ks)
│   ├── soil.py             SoilGrids + Saxton & Rawls
│   ├── terrain.py          NMT: spadki, spływ, zagłębienia
│   ├── crops.py            Kc, korzenie, okresy krytyczne
│   ├── http.py             pobieranie + cache + tryb offline
│   ├── output.py           raport tekstowy i GeoJSON
│   ├── satellite.py        Sentinel-2: NDVI, NDMI, najsuchsze miejsce
│   ├── hydrology.py        BDOT10k: rowy, cieki, zbiorniki, mokradła, lasy
│   └── ai_report.py        [plan] raport AI
├── api/                    serwer FastAPI (działa: main.py)
│   ├── main.py             aplikacja, CORS, obsługa błędów
│   ├── routes.py           endpointy (patrz API.md)
│   ├── schemas.py          modele Pydantic = kontrakt z frontem
│   └── jobs.py             zadania w tle + postęp
├── web/                    podstawowy interfejs (działa: index.html, app.js, style.css)
├── tests/                  [plan] testy reguł i bilansu na stałych danych
└── demo/                   gotowe wyniki działek demo (JSON + GeoJSON)
```

## Rdzeń: przepływ jednej analizy

Funkcja `wodnik.analysis.analyse(parcel_id | point, on, crop_key)`:

| # | Krok | Moduł | Wynik |
|---|---|---|---|
| 1 | działka | `parcel` | geometria, powierzchnia, gmina |
| 2 | pogoda + tło wieloletnie | `weather` | szereg 150 dni + percentyle z 10 lat |
| 3 | gleba | `soil` | uziarnienie, próchnica, pojemność wodna |
| 4 | teren | `terrain` | spadki, punkty odpływu, zagłębienia, dopływ z zewnątrz |
| 5 | bilans wody | `waterbalance` | wyczerpanie, próg stresu, dni stresu |
| 6 | ocena → przyczyny → retencja → agro → nawadnianie | `analysis` | obiekt `Report` |

Kroki 2–4 są niezależne, więc w serwerze można je wykonać równolegle (`asyncio` / wątki), co skróci pierwsze przeliczenie z ok. 20–40 s do czasu najwolniejszego źródła (zwykle NMT).

## Kontrakt danych: obiekt `Report`

Backend zwraca to, co dziś produkuje `Report.to_dict()`:

| Pole | Zawartość |
|---|---|
| `parcel` | id, gmina, obręb, powierzchnia, środek, geometria WGS84 (GeoJSON) |
| `date`, `crop` | parametry analizy |
| `risk_level`, `risk_summary` | niskie / umiarkowane / wysokie + zdanie opisu |
| `assessment[]` | 4–5 wskaźników (`Item`) |
| `causes[]`, `main_cause` | przyczyny z siłą (słaba / umiarkowana / silna) |
| `retention[]`, `agrotechnics[]`, `irrigation[]` | rekomendacje (`Item`), część z `location` (lat/lon) |
| `uncertainty[]`, `confidence` | ograniczenia i pewność całości |
| `data_sources[]` | lista użytych źródeł |
| `raw` | surowe liczby (bilans, percentyle, gleba, teren) |

**Braki względem potrzeb interfejsu (do dodania w rdzeniu):**
- `timeseries`: dziennie `date`, `precip`, `et0`, `depletion`, `raw_threshold` do wykresu bilansu wody,
- `layers`: GeoJSON z liniami spływu i zagłębieniami do mapy działań (dziś są tylko punkty),
- `meta`: czas obliczeń, wersja reguł, które źródła były z cache.

## Proponowany stos technologiczny **[do decyzji zespołu]**

| Warstwa | Propozycja | Dlaczego |
|---|---|---|
| Serwer | FastAPI (Python) | rdzeń już jest w Pythonie, walidacja i dokumentacja OpenAPI za darmo |
| Front | Vite + React lub czysty HTML/JS | szybki start; liczy się prostota obsługi |
| Mapa | Leaflet + ortofotomapa GUGiK (WMTS, otwarta) | bez kluczy API, bez opłat |
| Wykresy | lekka biblioteka (np. uPlot / Chart.js) | jeden wykres bilansu wystarczy |
| Raport AI | Claude API (model konfigurowalny zmienną środowiskową) | patrz RAPORT_AI.md |
| Hosting demo | dowolny VPS lub kontener | działa też lokalnie |

Warianty są równoważne dla rdzenia. Jeśli czasu jest mało: jeden plik HTML z Leaflet + `fetch()` do FastAPI wystarczy do demo.

## Bezpieczeństwo (kryterium „podstawowe mechanizmy bezpieczeństwa”)

- Walidacja wejścia: format ID działki (regex), data w sensownym zakresie, uprawa z listy zamkniętej, współrzędne w granicach Polski.
- Limit rozmiaru działki (już w `terrain.py`: bok do 2,2 km) i limit zapytań na IP.
- Klucz API do Claude wyłącznie w zmiennej środowiskowej (`ANTHROPIC_API_KEY`), nigdy w repo. `.env` jest w `.gitignore`.
- CORS ograniczony do adresu frontu.
- Brak danych osobowych: działka ewidencyjna to dane publiczne, nie zapisujemy tożsamości użytkownika.
- Timeouty i ponowienia dla zewnętrznych API (są w `http.py`); błędy źródeł nie wywalają całej analizy, tylko trafiają do `uncertainty`.

## Testy **[plan]**

- Bilans FAO-56 na stałym szeregu pogody: wynik porównany z ręcznie policzonym.
- Reguły przyczyn: syntetyczne `Soil`/`Terrain`/pogoda → oczekiwana główna przyczyna.
- Parser ULDK na zapisanych odpowiedziach.
- Test kontraktu: odpowiedź API zgodna ze schematem Pydantic.
- Regresja demo: 3 działki z `demo/` dają ten sam poziom ryzyka.
