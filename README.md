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

Pierwsze przeliczenie nowej działki trwa ok. 20–40 s (pobieranie tła wieloletniego i NMT), kolejne kilka sekund.

## Jak to działa

| Moduł | Co robi | Metoda |
|---|---|---|
| `parcel.py` | granice działki | ULDK (GUGiK) |
| `weather.py` | opad, ET₀, temp. maks., wilgotność gleby; tło wieloletnie 1995–2025 | ERA5 / ERA5-Land przez Open-Meteo |
| `waterbalance.py` | dobowy bilans wody w strefie korzeniowej, stres wodny | FAO-56 (Allen i in.), współczynnik Kc, TAW/RAW/Ks |
| `soil.py` | uziarnienie, węgiel organiczny, pojemność wodna | SoilGrids 2.0 + pedotransfer Saxton & Rawls (2006) |
| `terrain.py` | spadki, punkty odpływu, zagłębienia, dopływ z zewnątrz | NMT LIDAR 1 m → 5 m, priority-flood, D8, akumulacja spływu |
| `crops.py` | Kc miesięczne, głębokość korzeni, okresy krytyczne | uproszczone tabele FAO-56 |
| `analysis.py` | ocena, przyczyny, rekomendacje, niepewność | jawne reguły (progi opisane w kodzie) |

**Ocena sytuacji wodnej** łączy trzy niezależne wskaźniki: bilans FAO-56 dla uprawy, klimatyczny bilans wodny na tle 31 lat oraz wilgotność gleby z ERA5-Land na tle 31 lat. Osobno pokazujemy **skłonność miejsca do suszy** (ile lat z wyraźnym deficytem w tym terminie), żeby odróżnić bieżącą suszę od stałej podatności.

**Przyczyny** to trzy grupy z materiału naukowego KOWR: deficyt opadu i upał, słaba gleba, nadmierny spływ. Każda dostaje siłę (słaba / umiarkowana / silna) z uzasadnieniem.

## Dane i licencje

| Źródło | Dane | Licencja / warunki |
|---|---|---|
| GUGiK – ULDK | granice działek | dane otwarte, bezpłatne (ustawa Prawo geodezyjne i kartograficzne) |
| GUGiK – NMT (WCS) | model terenu z LIDAR, 1 m | dane otwarte, bezpłatne (jw.) |
| Copernicus ERA5 / ERA5-Land | reanaliza meteorologiczna i glebowa | licencja Copernicus: bezpłatna, z podaniem źródła |
| Open-Meteo | dostęp API do ERA5 i prognoz | dane CC BY 4.0; **darmowe API tylko do użytku niekomercyjnego**, wdrożenie wymaga planu komercyjnego lub pobierania ERA5 z Copernicus CDS |
| ISRIC SoilGrids 2.0 | uziarnienie, węgiel organiczny | CC BY 4.0 |

### Komponenty programowe

| Biblioteka | Licencja |
|---|---|
| numpy, scipy | BSD-3-Clause |
| rasterio (z GDAL) | BSD-3-Clause (GDAL: MIT) |
| shapely | BSD-3-Clause |
| pyproj (z PROJ) | MIT |
| requests | Apache-2.0 |
| urllib3 | MIT |

Wszystkie licencje pozwalają na przeniesienie praw do rozwiązania na KOWR i dalsze wykorzystanie.

## Ograniczenia (wprost pokazywane w raporcie)

- Pogoda z reanalizy (siatka ok. 9–25 km): lokalne burze mogą dać inny opad.
- Gleba z modelu SoilGrids (250 m). Docelowo mapa glebowo-rolnicza IUNG lub wyniki badań gleby.
- Bilans FAO-56 zakłada pełne uwilgotnienie gleby na początku okresu (150 dni przed datą).
- Próg „roku z deficytem” (bilans 60 dni ≤ −100 mm) to heurystyka do kalibracji z metodyką IUNG.
- Dla dat z ostatnich ok. 6 dni brak wilgotności gleby z ERA5-Land (opóźnienie reanalizy).

## Plan rozwoju

- Sentinel-2 (NDVI, NDMI) przez Copernicus Data Space: potwierdzenie stresu na zdjęciach satelitarnych
- BDOT10k: rowy, cieki, zadrzewienia, czyli dokładniejsza lokalizacja zastawek
- Mapa glebowo-rolnicza IUNG zamiast SoilGrids
- Interfejs webowy z mapą (wynik JSON/GeoJSON jest już gotowy)
