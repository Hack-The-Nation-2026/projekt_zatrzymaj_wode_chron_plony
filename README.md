# Wodnik – prototyp analizy wodnej działki

Zadanie KOWR „Zatrzymaj wodę, chroń plony” · HackNation 2026

Dla **działki ewidencyjnej, daty i uprawy** Wodnik przeprowadza analizę w kolejności wymaganej przez KOWR:

> ocena sytuacji wodnej → identyfikacja przyczyn → rekomendacje retencyjne → działania agrotechniczne → ewentualne nawadnianie

Każdy wniosek ma **uzasadnienie** (konkretne wartości i źródło danych) oraz **poziom pewności**. Logika jest regułowa i jawna, bez modelu językowego.

## Uruchomienie

Wymagany Python 3.9+.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Aplikacja webowa (serwer + interfejs)

```bash
.venv/bin/uvicorn api.main:app --port 8000
```

Otwórz <http://localhost:8000>. Wybierz działkę kliknięciem na mapie albo numerem, ustaw datę i uprawę, kliknij „Sprawdź wodę”. Przycisk „Przykład: Łazisko…” ładuje gotowy wynik z katalogu `demo/` (działa bez internetu i bez limitów API). Dokumentacja API: <http://localhost:8000/docs>.

### Wiersz poleceń

```bash
.venv/bin/python -m wodnik --dzialka 101609_2.0011.352 --data 2026-06-15 --uprawa pszenica_ozima
```

Opcje:

| Opcja | Opis |
|---|---|
| `--dzialka ID` | pełny identyfikator działki, np. `101609_2.0011.352` |
| `--punkt lat,lon` | zamiast ID: punkt na działce (WGS84) |
| `--data RRRR-MM-DD` | data analizy (domyślnie dziś; dla dat świeżych dołącza prognozę 7 dni) |
| `--uprawa` | `pszenica_ozima`, `jeczmien_jary`, `rzepak_ozimy`, `kukurydza`, `ziemniaki`, `burak_cukrowy`, `uzytki_zielone` |
| `--json plik` | pełny wynik (do interfejsu webowego) |
| `--geojson plik` | działka i miejsca rekomendacji do mapy |

**Tryb demo bez internetu:** każda odpowiedź API jest zapisywana w `.cache/http`. Po jednym przeliczeniu działki można uruchomić:

```bash
WODNIK_OFFLINE=1 .venv/bin/python -m wodnik --dzialka 101609_2.0011.352 --data 2026-06-15
```

Pierwsze przeliczenie nowej działki trwa ok. 30–90 s (tło wieloletnie, NMT, zdjęcia satelitarne), kolejne kilka sekund.

> **Uwaga na limit Open-Meteo.** Darmowy plan ma dzienny limit zapytań; tło wieloletnie (31 lat) zużywa go szybko. Przy przekroczeniu serwer zwraca czytelny błąd `SOURCE_RATE_LIMITED`. Przed prezentacją przelicz działki demo i zapisz je w `demo/` (format jak w `demo/lazisko_2026-06-15.json`).

## Dokumentacja

| Dokument | Zawartość |
|---|---|
| [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) | struktura projektu, przepływ analizy, kontrakt danych, stos, bezpieczeństwo |
| [docs/UI.md](docs/UI.md) | strony interfejsu, makiety, zasady prostoty obsługi |
| [docs/API.md](docs/API.md) | zapytania do serwera (endpointy, żądania, odpowiedzi, błędy) |
| [docs/RAPORT_AI.md](docs/RAPORT_AI.md) | raport AI na końcu analizy: prompt, kontrola liczb, zabezpieczenia |

Stan: **działają** rdzeń analizy (`wodnik/`, w tym satelita), serwer FastAPI (`api/`) i podstawowy interfejs (`web/`). **Raport AI** jest zaprojektowany, ale jeszcze niezbudowany.

## Jak to działa

| Moduł | Co robi | Metoda |
|---|---|---|
| `parcel.py` | granice działki | ULDK (GUGiK) |
| `weather.py` | opad, ET₀, temp. maks., wilgotność gleby; tło wieloletnie 1995–2025 | ERA5 / ERA5-Land przez Open-Meteo |
| `waterbalance.py` | dobowy bilans wody w strefie korzeniowej, stres wodny | FAO-56 (Allen i in.), współczynnik Kc, TAW/RAW/Ks |
| `soil.py` | uziarnienie, węgiel organiczny, pojemność wodna | SoilGrids 2.0 + pedotransfer Saxton & Rawls (2006) |
| `terrain.py` | spadki, punkty odpływu, zagłębienia, dopływ z zewnątrz | NMT LIDAR 1 m → 5 m, priority-flood, D8, akumulacja spływu |
| `satellite.py` | stan roślin: NDVI (zieloność), NDMI (woda w roślinach), zmiana między zdjęciami, najsuchsze miejsce na polu | Sentinel-2 L2A, maska chmur SCL, wycinek działki z plików COG |
| `crops.py` | Kc miesięczne, głębokość korzeni, okresy krytyczne | uproszczone tabele FAO-56 |
| `analysis.py` | ocena, przyczyny, rekomendacje, niepewność | jawne reguły (progi opisane w kodzie) |
| `api/main.py` | serwer HTTP: działki, analiza w tle z postępem, GeoJSON, działki demo | FastAPI |
| `web/` | interfejs: mapa (ortofoto i granice działek GUGiK), formularz, wynik w 5 krokach | HTML + Leaflet, bez budowania |

**Ocena sytuacji wodnej** łączy cztery niezależne wskaźniki: bilans FAO-56 dla uprawy, klimatyczny bilans wodny na tle 31 lat, wilgotność gleby z ERA5-Land na tle 31 lat oraz stan roślin z Sentinel-2.

**Satelita** szuka najnowszego zdjęcia, na którym co najmniej 60% działki jest bez chmur (do 30 dni wstecz), i wcześniejszego o 2–5 tygodni do porównania. Progi NDMI (≥ 0,2 dobre uwodnienie, 0–0,2 umiarkowane, < 0 niskie, przy NDVI ≥ 0,4) są heurystyczne; spadek zieloności może też oznaczać naturalne dojrzewanie, co raport mówi wprost. Osobno pokazujemy **skłonność miejsca do suszy** (ile lat z wyraźnym deficytem w tym terminie), żeby odróżnić bieżącą suszę od stałej podatności.

**Przyczyny** to trzy grupy z materiału naukowego KOWR: deficyt opadu i upał, słaba gleba, nadmierny spływ. Każda dostaje siłę (słaba / umiarkowana / silna) z uzasadnieniem.

## Dane i licencje

| Źródło | Dane | Licencja / warunki |
|---|---|---|
| GUGiK – ULDK | granice działek | dane otwarte, bezpłatne (ustawa Prawo geodezyjne i kartograficzne) |
| GUGiK – NMT (WCS) | model terenu z LIDAR, 1 m | dane otwarte, bezpłatne (jw.) |
| Copernicus ERA5 / ERA5-Land | reanaliza meteorologiczna i glebowa | licencja Copernicus: bezpłatna, z podaniem źródła |
| Open-Meteo | dostęp API do ERA5 i prognoz | dane CC BY 4.0; **darmowe API tylko do użytku niekomercyjnego**, wdrożenie wymaga planu komercyjnego lub pobierania ERA5 z Copernicus CDS |
| ISRIC SoilGrids 2.0 | uziarnienie, węgiel organiczny | CC BY 4.0 |
| Copernicus Sentinel-2 L2A | zdjęcia satelitarne (pasma czerwone, NIR, SWIR, maska SCL) | dane Copernicus: bezpłatne i otwarte, także komercyjnie, z podaniem źródła |
| Earth Search (Element 84) + AWS Open Data | katalog STAC i pliki COG Sentinel-2 | publiczny, bez konta; dane na licencji Copernicus |
| GUGiK – ortofotomapa (WMS), granice działek (KIEG, WMS) | podkład mapy | dane otwarte GUGiK |
| OpenStreetMap | alternatywny podkład mapy | ODbL; kafelki OSM tylko do małego ruchu (polityka użycia OSMF) |

### Komponenty programowe

| Biblioteka | Licencja |
|---|---|
| fastapi, uvicorn, pydantic | MIT / BSD-3-Clause / MIT |
| Leaflet (frontend, z CDN unpkg) | BSD-2-Clause |
| numpy, scipy | BSD-3-Clause |
| rasterio (z GDAL) | BSD-3-Clause (GDAL: MIT) |
| shapely | BSD-3-Clause |
| pyproj (z PROJ) | MIT |
| requests | Apache-2.0 |
| urllib3 | MIT |
| anthropic (SDK, planowany, opcjonalny raport AI) | MIT |

Planowany raport AI korzysta z Claude API (warunki komercyjne Anthropic). Moduł jest opcjonalny: bez klucza API Wodnik działa w pełni, a raport jest szablonowy (patrz [docs/RAPORT_AI.md](docs/RAPORT_AI.md)).

Wszystkie licencje pozwalają na przeniesienie praw do rozwiązania na KOWR i dalsze wykorzystanie.

## Ograniczenia (wprost pokazywane w raporcie)

- Pogoda z reanalizy (siatka ok. 9–25 km): lokalne burze mogą dać inny opad.
- Gleba z modelu SoilGrids (250 m). Docelowo mapa glebowo-rolnicza IUNG lub wyniki badań gleby.
- Bilans FAO-56 zakłada pełne uwilgotnienie gleby na początku okresu (150 dni przed datą).
- Próg „roku z deficytem” (bilans 60 dni ≤ −100 mm) to heurystyka do kalibracji z metodyką IUNG.
- Dla dat z ostatnich ok. 6 dni brak wilgotności gleby z ERA5-Land (opóźnienie reanalizy).
- Satelita: piksel 10–20 m, chmury mogą uniemożliwić analizę; progi NDVI/NDMI heurystyczne, bez tła wieloletniego dla działki.
- Serwer trzyma zadania w pamięci (restart je kasuje, poza działkami demo).

## Plan rozwoju

- Scenariusze ryzyka na najbliższe tygodnie (bilans FAO-56 puszczony z pogodą z 31 lat)
- Raport AI (projekt: [docs/RAPORT_AI.md](docs/RAPORT_AI.md))
- BDOT10k: rowy, cieki, zadrzewienia, czyli dokładniejsza lokalizacja zastawek
- Mapa glebowo-rolnicza IUNG zamiast SoilGrids
- Własne źródło ERA5 (Copernicus CDS) zamiast darmowego Open-Meteo: bez limitów i z licencją do wdrożenia
