# API: zapytania do serwera

Specyfikacja serwera **[plan]**, który opakowuje rdzeń `wodnik/` dla interfejsu webowego. Format: JSON, kodowanie UTF-8, prefiks `/api/v1`. Serwer w FastAPI wygeneruje też automatyczną dokumentację OpenAPI pod `/docs`.

## Przegląd endpointów

| Metoda | Ścieżka | Cel | Ekran UI |
|---|---|---|---|
| GET | `/health` | stan serwera i źródeł danych | (monitoring) |
| GET | `/crops` | lista upraw | 1 Start |
| GET | `/parcels/resolve` | działka z punktu (kliknięcie, GPS) | 1 Start |
| GET | `/parcels/search` | działka po numerze | 1 Start |
| POST | `/analyses` | uruchom analizę | 1 → 2 |
| GET | `/analyses/{id}` | postęp i wynik | 2, 3, 5 |
| GET | `/analyses/{id}/geojson` | warstwy mapy | 4 Mapa |
| POST | `/analyses/{id}/report` | raport AI | 6 Raport |
| GET | `/analyses/{id}/report` | pobierz wygenerowany raport | 6 Raport |
| GET | `/demo` | lista przykładowych działek | 1 Start |

## Konwencje

- Daty: `RRRR-MM-DD`. Współrzędne: WGS84, `lat`/`lon`.
- Identyfikator działki: `TERYT_gminy.obręb.numer`, np. `101609_2.0011.352`.
- Błędy mają jeden format (niżej). Kody HTTP: `400` zły parametr, `404` nie znaleziono, `422` błąd walidacji, `429` za dużo zapytań, `502` źródło danych nie odpowiada, `504` przekroczony czas.

```json
{ "error": { "code": "PARCEL_NOT_FOUND", "message": "Nie znaleziono działki.", "hint": "Dotknij działki na mapie." } }
```

| `code` | Znaczenie |
|---|---|
| `PARCEL_NOT_FOUND` | ULDK nie zna takiej działki |
| `PARCEL_TOO_LARGE` | działka > 2,2 km w poprzek |
| `INVALID_INPUT` | zła data, uprawa lub współrzędne |
| `SOURCE_UNAVAILABLE` | zewnętrzne API nie odpowiedziało (z polem `source`) |
| `NO_DATA` | brak pogody dla daty (np. data w przyszłości > 15 dni) |
| `RATE_LIMITED` | limit zapytań |

---

## `GET /health`

```json
{ "status": "ok", "version": "0.1.0", "offline_mode": false,
  "sources": { "uldk": "ok", "weather": "ok", "soil": "ok", "dem": "ok" } }
```

## `GET /crops`

```json
[ { "key": "pszenica_ozima", "name": "pszenica ozima",
    "critical_label": "strzelanie w źdźbło – kłoszenie (maj–czerwiec)" },
  { "key": "ziemniaki", "name": "ziemniaki", "critical_label": "zawiązywanie bulw (czerwiec–lipiec)" } ]
```

Dane z `crops.CROPS`.

## `GET /parcels/resolve?lat=51.545&lon=19.949`

Działka, w której leży punkt (`parcel.by_point`).

```json
{ "id": "101609_2.0011.352", "commune": "Tomaszów Mazowiecki", "region": "Łazisko",
  "county": "powiat tomaszowski", "voivodeship": "łódzkie",
  "area_ha": 3.01, "center": { "lat": 51.54499, "lon": 19.94934 },
  "geometry": { "type": "Polygon", "coordinates": [[[19.9497, 51.5503]]] } }
```

## `GET /parcels/search?q=Łazisko 352`

Wyszukiwanie po fragmencie opisu lub pełnym ID. Zwraca listę (do 5 trafień) w formacie jak wyżej, bez geometrii (tylko `id`, `commune`, `region`, `area_ha`, `center`).
**Do zweryfikowania:** ULDK ma osobne zapytanie dla numeru i obrębu (`GetParcelByIdOrNr`); sprawdzić format przed wdrożeniem.

---

## `POST /analyses`

Uruchamia analizę. Dla działki z cache odpowiedź jest natychmiastowa, dla nowej trwa do kilkudziesięciu sekund, więc serwer zwraca zadanie, a front odpytuje o postęp.

**Żądanie** (wymagane `parcel_id` albo `point`):

```json
{ "parcel_id": "101609_2.0011.352",
  "point": null,
  "date": "2026-06-15",
  "crop": "pszenica_ozima",
  "ai_report": false }
```

| Pole | Typ | Uwagi |
|---|---|---|
| `parcel_id` | string | regex `^\d{6,7}_\d\.\d{4}\.[\w/]+$` |
| `point` | `{lat, lon}` | tylko gdy brak `parcel_id`; w granicach Polski |
| `date` | string | domyślnie dziś; nie wcześniej niż 1995, nie później niż dziś + 7 dni |
| `crop` | string | klucz z `/crops` |
| `ai_report` | bool | czy od razu wygenerować raport AI po analizie |

**Odpowiedź `202 Accepted`:**

```json
{ "id": "a1b2c3d4", "status": "running", "poll_url": "/api/v1/analyses/a1b2c3d4" }
```

Identyczne zapytanie (te same `parcel_id`, `date`, `crop`) zwraca istniejący wynik zamiast liczyć ponownie (klucz cache = hash wejścia).

## `GET /analyses/{id}`

Wynik lub postęp. Front odpytuje co 1–2 s, dopóki `status` ≠ `running`.

**W trakcie:**

```json
{ "id": "a1b2c3d4", "status": "running",
  "progress": [
    { "step": "parcel",  "label": "Granice działki",               "state": "done" },
    { "step": "weather", "label": "Pogoda z ostatnich miesięcy",   "state": "done" },
    { "step": "soil",    "label": "Gleba",                         "state": "running" },
    { "step": "terrain", "label": "Ukształtowanie terenu",         "state": "pending" },
    { "step": "analysis","label": "Wnioski i zalecenia",           "state": "pending" } ] }
```

**Gotowe** (`status`: `done`; `partial` gdy brakowało źródła):

```json
{ "id": "a1b2c3d4", "status": "done",
  "report": {
    "parcel": { "id": "101609_2.0011.352", "gmina": "Tomaszów Mazowiecki", "powierzchnia_ha": 3.01 },
    "date": "2026-06-15", "crop": "pszenica ozima",
    "risk_level": "umiarkowane",
    "risk_summary": "Zapas wody się kurczy; warto działać zanim pojawi się wyraźny stres.",
    "assessment": [ { "title": "…", "detail": "…", "because": ["…"], "confidence": "średnia" } ],
    "causes": [ { "key": "gleba", "name": "Gleba słabo magazynuje wodę", "strength": "silna", "score": 4, "because": ["…"] } ],
    "main_cause": "Gleba słabo magazynuje wodę",
    "retention":    [ { "title": "…", "detail": "…", "because": ["…"], "confidence": "średnia",
                        "location": { "lat": 51.550649, "lon": 19.949855, "maps": "https://…" }, "priority": 1 } ],
    "agrotechnics": [ ],
    "irrigation":   [ ],
    "uncertainty":  [ "…" ],
    "confidence": "średnia",
    "data_sources": [ "GUGiK – ULDK", "Open-Meteo archive (ERA5/ERA5-Land)" ],
    "raw": { "kbw60_mm": -127.0, "wyczerpanie_mm": 69.0, "TAW_mm": 106.0, "RAW_mm": 58.0 } },
  "timeseries": [ { "date": "2026-06-14", "precip": 0.0, "et0": 4.8, "depletion": 66.1, "raw_threshold": 58.0 } ],
  "meta": { "computed_ms": 6400, "from_cache": ["uldk", "weather"], "rules_version": "0.1.0" } }
```

Kształt `report` jest zgodny z `Report.to_dict()`. Pola `timeseries` i `meta` trzeba dodać w rdzeniu (patrz [ARCHITEKTURA.md](ARCHITEKTURA.md)).

**Błąd:** `status: "failed"` + obiekt `error` jak w sekcji Konwencje.

## `GET /analyses/{id}/geojson`

Warstwy do mapy (`FeatureCollection`). Dziś rdzeń daje działkę i punkty rekomendacji (`output.geojson`), docelowo dochodzą linie spływu i zagłębienia.

```json
{ "type": "FeatureCollection", "features": [
  { "type": "Feature", "geometry": { "type": "Polygon", "coordinates": [] },
    "properties": { "rodzaj": "dzialka", "ryzyko": "umiarkowane" } },
  { "type": "Feature", "geometry": { "type": "Point", "coordinates": [19.949855, 51.550649] },
    "properties": { "rodzaj": "rekomendacja", "tytul": "Zatrzymaj wodę w miejscu odpływu", "opis": "…" } } ] }
```

---

## Raport AI

Szczegóły generowania i zabezpieczeń: [RAPORT_AI.md](RAPORT_AI.md).

### `POST /analyses/{id}/report`

```json
{ "style": "rolnik", "length": "short" }
```

| Pole | Wartości | Znaczenie |
|---|---|---|
| `style` | `rolnik` (domyślnie), `doradca` | prosty język lub techniczny z odwołaniami do danych |
| `length` | `short` (ok. 200 słów), `full` (ok. 500) | długość opisu |

**Odpowiedź `200`** (generowanie trwa kilka sekund; można też zwrócić `202` jak wyżej):

```json
{ "report_id": "r9x8",
  "analysis_id": "a1b2c3d4",
  "source": "ai",
  "model": "claude-opus-5-5",
  "generated_at": "2026-11-21T12:30:00Z",
  "markdown": "## Podsumowanie\nNa Twojej działce …",
  "disclaimer": "Tekst wygenerowany przez AI na podstawie wyników analizy. Sprawdź zalecenia przed działaniem.",
  "checks": { "numbers_verified": true } }
```

| `source` | Kiedy |
|---|---|
| `ai` | opis wygenerowany i przeszedł kontrolę liczb |
| `template` | AI niedostępne lub tekst odrzucony przez kontrolę, zwrócony szablon z `output.text()` |

### `GET /analyses/{id}/report`

Zwraca ostatnio wygenerowany raport (ten sam format) lub `404`.

### `GET /demo`

```json
[ { "id": "demo-lazisko", "title": "Łazisko, pszenica, czerwiec 2026", "parcel_id": "101609_2.0011.352",
    "date": "2026-06-15", "crop": "pszenica_ozima", "analysis_id": "demo-lazisko" } ]
```

Wynik jest zapisany w `demo/`, ładowany bez sieci przez `GET /analyses/demo-lazisko`.

---

## Przykład w przeglądarce

```js
const r = await fetch("/api/v1/analyses", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ parcel_id, date, crop }),
});
const { id } = await r.json();
let a;
do { await new Promise(t => setTimeout(t, 1500)); a = await (await fetch(`/api/v1/analyses/${id}`)).json(); }
while (a.status === "running");
```

## Wymagania niefunkcjonalne

| Obszar | Wymaganie |
|---|---|
| Czas | analiza z cache poniżej 3 s, bez cache do ok. 40 s (z paskiem postępu) |
| Limit | np. 20 analiz na minutę na IP, raport AI 5 na minutę |
| Współbieżność | kilka analiz równolegle; to samo wejście liczone raz |
| Cache wyników | w pamięci lub na dysku, klucz = hash `{parcel_id, date, crop}` |
| Logi | bez danych osobowych; źródła, czasy, kody błędów |
| Konfiguracja | zmienne środowiskowe: `WODNIK_OFFLINE`, `WODNIK_CACHE`, `ANTHROPIC_API_KEY`, `WODNIK_AI_MODEL`, `WODNIK_CORS_ORIGIN` |
