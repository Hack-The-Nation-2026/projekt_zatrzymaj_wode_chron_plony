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
| POST | `/auth/register` | załóż konto (od razu loguje) | 8 Logowanie |
| POST | `/auth/login` | zaloguj, zwraca token | 8 Logowanie |
| POST | `/auth/logout` | unieważnij token | 9 Profil |
| GET | `/me` | dane zalogowanego użytkownika | 9 Profil |
| GET | `/me/reports` | historia raportów | 9 Profil |
| GET | `/me/reports/{id}` | pełny raport z historii | 9 → 3 |
| GET | `/me/reports/{id}/raport` | raport z historii do druku (HTML) | 9 Profil |
| DELETE | `/me/reports/{id}` | usuń raport z historii | 9 Profil |
| POST | `/me/reports` | dopisz gotową analizę do historii | 3 Wynik |
| POST | `/chat` | asystent: odpowiedź na pytanie o raport | 3 Wynik |

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
    "raw": { "kbw60_mm": -127.0, "wyczerpanie_mm": 69.0, "TAW_mm": 106.0, "RAW_mm": 58.0 },
    "scenarios": {
      "horizon_days": 30, "years": 10, "in_stress_now": false, "level": "umiarkowane",
      "p_stress_14": 0.35, "p_stress_30": 0.55, "p_severe_30": 0.2, "p_recovery_30": 0.0,
      "median_onset_day": 12, "water_needed_p50_mm": 38.0, "water_needed_p90_mm": 74.0,
      "forecast_days_used": 0,
      "summary": "W 4 z 10 scenariuszy pogodowych roślina wejdzie w stres wodny w ciągu 14 dni, a w 6 z 10 w ciągu 30 dni.", "period": "2016–2025",
      "envelope": [ { "day": 1, "date": "2026-06-16", "p10": 52.1, "p50": 55.0, "p90": 57.3 } ] } },
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
[ { "id": "demo-lazisko_352_2026_06_15", "title": "Łazisko, pszenica, czerwiec 2026", "parcel_id": "101609_2.0011.352",
    "date": "2026-06-15", "crop": "pszenica_ozima", "analysis_id": "demo-lazisko_352_2026_06_15" } ]
```

Wynik jest zapisany w `demo/`, ładowany bez sieci przez `GET /analyses/demo-lazisko_352_2026_06_15`.

---

## Dane do wykresów (`report.charts`)

W pełnym wyniku (`GET /analyses/{id}` → `report`, a także w raportach z historii) jest pole `charts`.
Starsze wyniki (np. stare demo) go nie mają, więc frontend musi to obsłużyć.

```json
"charts": {
  "daily": {                                   // dzień po dniu, ok. 150 dni do daty analizy włącznie
    "dates": ["2026-01-16", "…", "2026-06-15"],
    "precip_mm": [0.0, 4.2, null, "…"],         // opad (ERA5); null = brak danych
    "et0_mm": [0.6, 0.8, "…"],                  // parowanie referencyjne ET0
    "water_left_mm": [106.0, "…", 37.2],        // zapas wody dostępnej dla roślin = TAW − wyczerpanie (FAO-56)
    "taw_mm": 106.0,                            // pełny zapas (góra osi)
    "stress_below_mm": 47.7                     // poniżej tego zapasu roślina jest w stresie (TAW − RAW)
  },
  "years": {
    "items": [ { "year": 2016, "kbw60_mm": -41.3, "current": false }, "…",
               { "year": 2026, "kbw60_mm": -126.8, "current": true } ],
    "deficit_threshold_mm": -100.0,             // próg „roku z wyraźnym deficytem”
    "label": "bilans opad − parowanie z 60 dni przed 15.06"
  }
}
```

Wykres zapasu wody łączy się ze scenariuszami: ostatni punkt `water_left_mm` to „dziś”, a `scenarios.envelope`
(dni 1–30) to dalszy ciąg. Wyrażony jest jako wyczerpanie, więc na wykresie rysuje się `taw_mm − p50` itd.
Gotowe rysowanie: `web/charts.js` (SVG jako tekst), `web/Charts.jsx` (komponenty React), `wodnik/charts.py`
(raport do druku).

---

## „Co da retencja” (`report.what_if`)

```json
"what_if": {
  "summary": "Przy ulewie 50 mm z działki i sąsiednich pól spłynie ok. 1026 m³ wody …",
  "storms": [ { "rain_mm": 30, "runoff_mm": 1.7, "volume_parcel_m3": 51, "volume_inflow_m3": 137, "volume_total_m3": 188 },
              { "rain_mm": 50, "runoff_mm": 9.3, "volume_parcel_m3": 280, "volume_inflow_m3": 747, "volume_total_m3": 1026 } ],
  "measures": [ { "key": "wal", "name": "Wał lub próg w miejscu odpływu", "value": 433, "unit": "m", "detail": "…" },
                { "key": "oczko", "name": "Oczko wodne lub mokradło w naturalnym obniżeniu", "value": 781, "unit": "m³", "detail": "…" },
                { "key": "materia", "name": "Więcej materii organicznej …", "value": 5.2, "unit": "mm", "detail": "…" } ],
  "root_zone": { "taw_before_mm": 106, "taw_after_mm": 111.2, "stress_days_season_before": 47, "stress_days_season_after": 46, "…": "…" },
  "curve_number": 75, "hydrologic_group": "B", "parcel_ha": 3.01, "inflow_ha": 8.04, "slope_pct": 1.9,
  "assumptions": ["…"]
}
```

`wal` i `oczko` są tylko wtedy, gdy jest analiza terenu (NMT); `materia` – gdy są dane glebowe. Starsze wyniki nie mają
pola `what_if`. Dlaczego ulewa, a nie cały sezon: dobowe opady ERA5 to średnia dla obszaru 9–25 km i rzadko przekraczają
15–20 mm, więc metoda SCS-CN nie widzi w nich spływu (opis w `wodnik/whatif.py`). W frontendzie: `report.whatIf`, `WhatIf.jsx`.

---

## Asystent (`POST /chat`)

```json
// żądanie: historia rozmowy (ostatnia wiadomość od użytkownika) i raport, o który pytamy (opcjonalnie)
{ "messages": [ { "role": "user", "content": "Co zrobić najpierw?" } ],
  "analysis_id": "a1b2c3d4e5" }          // albo "report_id": 3 (raport z historii, wymaga tokena)
// odpowiedź
{ "reply": "…", "source": "ai", "model": "gpt-5.4-mini" }   // source "fallback": bez AI, skrót z raportu
```

Model: OpenAI przez LangChain (`api/chat.py`), klucz `OPENAI_API_KEY` w `.env`, model `WODNIK_CHAT_MODEL`.
Bez klucza albo przy błędzie modelu serwer zwraca `source: "fallback"` (najważniejsze wnioski z raportu), więc czat
nigdy nie psuje aplikacji. Limity: do 40 wiadomości, 4000 znaków na wiadomość, limit pytań na IP (`429`).
Model dostaje opis raportu bez geometrii i danych konta. W frontendzie: `api.chat({ messages, report })`.

---

## Konto i historia raportów

Konto jest opcjonalne: analiza działa bez logowania. Zalogowany użytkownik dostaje każdy wynik także w swojej
historii, która przetrwa restart serwera (SQLite, plik `data/wodnik.db`, zmienna `WODNIK_DB`).

**Uwierzytelnienie:** nagłówek `Authorization: Bearer <token>`. Token jest ważny 30 dni; serwer trzyma tylko jego
skrót SHA-256. Hasła: PBKDF2-HMAC-SHA256, 200 000 iteracji, losowa sól. Logowanie i rejestracja mają limit prób na IP.

### `POST /auth/register` i `POST /auth/login`

```json
// żądanie (name tylko przy rejestracji, opcjonalne; hasło min. 8 znaków)
{ "email": "jan@example.com", "password": "********", "name": "Jan" }
// odpowiedź: 201 (rejestracja) / 200 (logowanie)
{ "token": "…", "user": { "id": 1, "email": "jan@example.com", "name": "Jan", "created_at": "2026-11-21T16:41:44Z" } }
```

Błędy: `400 INVALID_INPUT` (zły e-mail, za krótkie hasło), `409 EMAIL_TAKEN`, `401 BAD_CREDENTIALS`
(ten sam komunikat dla złego e-maila i złego hasła), `429 RATE_LIMITED`.

### `POST /auth/logout` → `204`. `GET /me` → użytkownik + `reports_count`, bez tokena `401 UNAUTHORIZED`.

### `GET /me/reports`

```json
[ { "id": 3, "analysis_id": "a1b2c3d4e5", "parcel_id": "101609_2.0011.352", "place": "Łazisko, gm. Tomaszów Mazowiecki",
    "date": "2026-06-15", "crop": "pszenica ozima", "risk_level": "wysokie", "saved_at": "2026-11-21T16:41:45Z" } ]
```

Najnowsze pierwsze. `GET /me/reports/{id}` zwraca to samo plus `report` (pełny wynik jak w `GET /analyses/{id}`).
Cudzy lub nieistniejący raport: `404`. Ta sama analiza trafia do historii tylko raz.

**Kiedy raport trafia do historii:** automatycznie, gdy `POST /analyses` wysłano z tokenem (także dla działek demo
i wyników z pamięci podręcznej). Gotową analizę zrobioną przed zalogowaniem można dopisać przez
`POST /me/reports` z `{ "analysis_id": "…" }`.

**Raport do druku z historii** wymaga tokena, więc zwykły link nie zadziała; frontend pobiera HTML z nagłówkiem
i otwiera go jako blob (gotowe w `web/api.js`: `api.openReportHtml(id)`).

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
