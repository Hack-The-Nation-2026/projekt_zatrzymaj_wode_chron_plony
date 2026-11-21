# Wodnik – cyfrowy asystent wody na działce rolnej

Zadanie KOWR „Zatrzymaj wodę, chroń plony – Inteligentne wsparcie gospodarowania wodą w rolnictwie” · HackNation 2026

Rolnik podaje **numer działki ewidencyjnej** (albo wskazuje ją na mapie), **uprawę** i **datę**. Wodnik pobiera dane
meteorologiczne, satelitarne, glebowe, hydrologiczne i przestrzenne, **sam liczy** ocenę sytuacji wodnej i przygotowuje
raport z zaleceniami w kolejności wymaganej przez KOWR:

> ocena sytuacji wodnej → identyfikacja przyczyn → rekomendacje retencyjne → działania agrotechniczne → ewentualne nawadnianie

Każdy wniosek ma **uzasadnienie** (konkretne wartości i źródło danych) oraz **poziom pewności**, a raport kończy się
listą **ograniczeń**. Brak danych jest komunikowany wprost.

Spis treści (zgodnie z pkt 4.2 opisu zadania):
1. [Instrukcja uruchomienia](#1-instrukcja-uruchomienia)
2. [Podstawowe funkcjonalności](#2-podstawowe-funkcjonalności)
3. [Architektura](#3-architektura)
4. [Źródła i zakresy danych](#4-źródła-i-zakresy-danych)
5. [Dane pobierane na bieżąco i wcześniej](#5-dane-pobierane-na-bieżąco-i-wcześniej)
6. [Biblioteki, usługi zewnętrzne i narzędzia AI](#6-biblioteki-usługi-zewnętrzne-i-narzędzia-ai)
7. [Licencje i warunki korzystania](#7-licencje-i-warunki-korzystania)
8. [Znane ograniczenia](#8-znane-ograniczenia)
9. [Weryfikacja wyników i rekomendacji](#9-weryfikacja-wyników-i-rekomendacji)

Dodatkowo: [skalowalność i koszty](#skalowalność-i-koszty-pkt-54--55), [bezpieczeństwo](#bezpieczeństwo-pkt-56),
[dokumentacja szczegółowa](#dokumentacja-szczegółowa), opis zgłoszenia: [docs/ZGLOSZENIE.md](docs/ZGLOSZENIE.md).

---

## 1. Instrukcja uruchomienia

Wymagania: Python 3.9+, Node.js 18+ (tylko do zbudowania interfejsu), dostęp do internetu. Działa na Windows, macOS i
Linux; rolnik korzysta z przeglądarki (Chrome, Firefox, Edge, Safari, Opera) bez instalowania czegokolwiek.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
.venv/bin/uvicorn api.main:app --port 8000
```

Na Windows zamiast `.venv/bin/` użyj `.venv\Scripts\`.

**Asystent AI (opcjonalnie):** skopiuj `.env.example` do `.env` i wpisz `OPENAI_API_KEY`. Serwer wczytuje `.env`
przy starcie; plik nie trafia do repozytorium. Bez klucza czat działa w trybie podstawowym (skrót z raportu).

| Adres | Co |
|---|---|
| <http://localhost:8000> | aplikacja dla rolnika (React, `web/`) |
| <http://localhost:8000/prosty/> | widok techniczny z mapą (ortofoto, granice działek, punkty zaleceń) |
| `http://localhost:8000/api/v1/analyses/{id}/raport` | raport do wydruku lub zapisu jako PDF |
| <http://localhost:8000/docs> | dokumentacja API (OpenAPI) |

**Wiersz poleceń** (ta sama analiza bez przeglądarki):

```bash
.venv/bin/python -m wodnik --dzialka 101609_2.0011.352 --data 2026-06-15 --uprawa pszenica_ozima
```

Uprawy: `pszenica_ozima`, `pszenica_jara`, `zyto`, `jeczmien_jary`, `rzepak_ozimy`, `kukurydza`, `ziemniaki`,
`burak_cukrowy`, `uzytki_zielone`. Opcje `--json` i `--geojson` zapisują pełny wynik i warstwy mapy.

**Działki demo** (wynik policzony wcześniej tym samym kodem, działa bez internetu – zabezpieczenie prezentacji):

```bash
.venv/bin/python -m wodnik.demo --dzialka 101609_2.0011.352 --data 2026-06-15 --uprawa pszenica_ozima
```

**Praca nad frontendem:** serwer jak wyżej, w drugim terminalu `cd web && npm run dev` (Vite przekazuje `/api` do portu 8000).

**Testy:** `.venv/bin/python tests/test_scenarios.py && .venv/bin/python tests/test_accounts.py && .venv/bin/python tests/test_charts.py && .venv/bin/python tests/test_chat.py && .venv/bin/python tests/test_whatif.py`

## 2. Podstawowe funkcjonalności

| Krok w raporcie | Co robi Wodnik | Na podstawie |
|---|---|---|
| Wybór działki | numer ewidencyjny, współrzędne albo kliknięcie na mapie | ULDK (GUGiK) |
| **1. Ocena sytuacji wodnej** | zapas wody w strefie korzeniowej, bilans opad − parowanie, wilgotność gleby, stan roślin z satelity, woda w otoczeniu, **podatność miejsca na suszę w ostatnich 10 latach**, **scenariusze na 30 dni** | ERA5, ERA5-Land, Sentinel-2, BDOT10k, FAO-56 |
| **2. Przyczyny** | deficyt opadu i upał / gleba słabo trzyma wodę / woda odpływa z pola (+ brak zadrzewień, oczek, mokradeł) | wszystkie powyższe + NMT, SoilGrids |
| **3. Retencja** | konkretne miejsca: odpływ wody z działki z kierunkiem i współrzędnymi, **zastawka, gdy jest tam rów (BDOT10k)**, oczka w naturalnych obniżeniach, pasy buforowe, retencja w rowach i ciekach w otoczeniu, zadrzewienia | NMT z LIDAR, BDOT10k |
| **4. Agrotechnika** | międzyplony, resztki pożniwne, uprawa ograniczająca parowanie, dobór gatunków przy częstych suszach | gleba, tło 10 lat |
| **5. Nawadnianie** (na końcu) | czy jest zasadne, kiedy i ile wody (mm i m³/ha), z uwzględnieniem opłacalności dla uprawy i prognozy deszczu | bilans FAO-56, scenariusze, prognoza |
| Co da retencja | wymiarowanie na ulewę 30 i 50 mm: ile m³ wody spłynie z działki i z sąsiednich pól, ile metrów wału ją zatrzyma, ile zmieszczą naturalne obniżenia (oczko), ile wody więcej zmieści gleba z większą ilością materii organicznej | SCS-CN (USDA TR-55), NMT, Saxton & Rawls, `wodnik/whatif.py` |
| Wykresy | zapas wody w glebie (ostatnie miesiące + scenariusze 30 dni), opad i parowanie dzień po dniu, ten rok na tle 10 lat; w aplikacji i w raporcie do druku | `charts` w wyniku, `wodnik/charts.py`, `web/charts.js` |
| Strona startowa | opis projektu, problem w liczbach, pitch, model biznesowy, logowanie i rejestracja; można też zacząć bez konta | `web/Landing.jsx` |
| Asystent (czat) | odpowiada na pytania rolnika o jego raport prostym językiem, opierając się tylko na danych z raportu | `api/chat.py`, LangChain + OpenAI |
| Konto i historia | zakładanie konta, logowanie, historia zapisanych raportów w profilu (otwórz, drukuj, usuń); konto jest opcjonalne | `api/accounts.py`, SQLite |
| Raport | data analizy i wygenerowania, źródła danych, ograniczenia, pewność; wydruk lub PDF | `GET /api/v1/analyses/{id}/raport`, PDF w aplikacji |

Interpretacja zdjęć satelitarnych **zależy od uprawy**: porównujemy zieloność z typowym zakresem dla danej uprawy
w danym miesiącu, a spadek zieloności w okresie dojrzewania (np. zboża w lipcu) albo po pokosie (łąki) nie jest
liczony jako susza.

## 3. Architektura

```
przeglądarka (web/ – React)  ──HTTP/JSON──▶  api/main.py (FastAPI)  ──▶  wodnik/ (analiza w Pythonie)
                                                                              │ równolegle:
          ULDK · ERA5/ERA5-Land (Open-Meteo) · SoilGrids · NMT LIDAR (WCS) · BDOT10k (WMS) · Sentinel-2 (STAC/COG)
```

| Moduł | Rola |
|---|---|
| `wodnik/parcel.py` | granice działki z ULDK (po numerze lub punkcie) |
| `wodnik/weather.py` | szereg dzienny 150 dni + prognoza 7 dni; tło: te same okna kalendarzowe w 10 latach przed datą |
| `wodnik/waterbalance.py` | dobowy bilans wody w strefie korzeniowej wg FAO-56 (TAW, RAW, Ks) |
| `wodnik/soil.py` | uziarnienie i węgiel organiczny → pojemność wodna (Saxton & Rawls 2006) |
| `wodnik/terrain.py` | NMT 1 m → 5 m, wypełnienie zagłębień, kierunki spływu D8, akumulacja: punkty odpływu, zagłębienia, dopływ z sąsiednich pól |
| `wodnik/hydrology.py` | rowy, cieki, kanały, wody powierzchniowe, mokradła, lasy z BDOT10k; odległości od działki i od punktów odpływu |
| `wodnik/satellite.py` | Sentinel-2: NDVI, NDMI, maska chmur, zmiana między zdjęciami, najsuchsze miejsce na polu |
| `wodnik/scenarios.py` | 30 dni do przodu: bilans FAO-56 z pogodą z każdego z 10 lat (prognoza zespołowa z danych historycznych) |
| `wodnik/crops.py` | parametry upraw (Kc, korzenie, okresy krytyczne, typowe NDVI, dojrzewanie) |
| `wodnik/analysis.py` | 5 kroków KOWR, reguły i progi (opisane w kodzie), niepewność |
| `wodnik/output.py` | raport tekstowy, raport HTML do druku, GeoJSON |
| `api/main.py` | API: działki, analiza w tle z postępem, raport, GeoJSON, działki demo, limit zapytań |
| `api/accounts.py` | konta (rejestracja, logowanie, tokeny) i historia raportów w SQLite (`data/wodnik.db`) |
| `web/`, `web-simple/` | interfejs dla rolnika i widok techniczny z mapą |

Pobieranie danych biegnie **równolegle**, a każda odpowiedź źródła trafia do pamięci podręcznej (`.cache/`).
Szczegóły: [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md), [docs/API.md](docs/API.md).

## 4. Źródła i zakresy danych

| Kategoria (pkt 3.3) | Źródło | Zakres przestrzenny | Zakres czasowy |
|---|---|---|---|
| przestrzenne: działki | GUGiK ULDK | cała Polska, granice działek ewidencyjnych | stan bieżący |
| przestrzenne: ukształtowanie terenu | GUGiK NMT z LIDAR, usługa WCS `DigitalTerrainModel` (`DTM_PL-EVRF2007-NH`, ASCII Grid; zapasowo `DTM_PL-KRON86-NH_TIFF`) | działka + 150 m; siatka 2,5 m z usługi uśredniona do 5 m | pomiary LIDAR z lat ok. 2011–2020 (zależnie od regionu) |
| przestrzenne: użytkowanie terenu | BDOT10k (lasy i zadrzewienia), ortofotomapa (podkład mapy) | działka + 500 m | stan bazy BDOT10k |
| meteorologiczne | ERA5 / ERA5-Land przez Open-Meteo: opad, ET₀ (FAO), temp. maks. | węzeł siatki ok. 9–25 km najbliższy działce | 150 dni przed datą; **10 lat przed rokiem analizy** (okna 60 dni przed i 30 dni po dacie); prognoza 7 dni dla dat bieżących |
| glebowe | ERA5-Land: wilgotność gleby 0–100 cm; ISRIC SoilGrids 2.0: piasek, ił, węgiel organiczny | punkt w środku działki (SoilGrids 250 m) | wilgotność: data analizy na tle 10 lat; SoilGrids: model statyczny |
| hydrologiczne | BDOT10k (GUGiK), usługa WMS `kompozycja_BDOT10k_WMS`: rowy melioracyjne, rzeki i strumienie, kanały, wody powierzchniowe, mokradła | działka + 500 m, siatka 2–4 m | stan bazy BDOT10k |
| satelitarne | Copernicus Sentinel-2 L2A z katalogu Earth Search (AWS Open Data): pasma czerwone, NIR, SWIR, maska SCL | wycinek działki, piksel 10–20 m | najnowsze bezchmurne zdjęcie do 30 dni przed datą + zdjęcie 2–5 tygodni wcześniejsze; archiwum od 2015/2017 |

## 5. Dane pobierane na bieżąco i wcześniej

**Wszystkie wyniki i rekomendacje liczy aplikacja** z danych źródłowych w chwili analizy; nie ma gotowych rekomendacji.

| Dane | Kiedy pobierane | Gdzie zapisywane |
|---|---|---|
| wszystkie źródła z pkt 4 | **na bieżąco**, przy pierwszej analizie danej działki i daty | `.cache/http/` (odpowiedzi API), `.cache/sat/` (wyniki satelitarne); data pobrania = data utworzenia pliku |
| ponowna analiza tej samej działki i daty | z pamięci podręcznej (te same dane, wynik w < 1 s) | jw. |
| działki demo w `demo/` | policzone wcześniej **tym samym kodem** komendą `python -m wodnik.demo`; data obliczenia w polu `generated_at` raportu | `demo/*.json` |

Prototyp nie korzysta z żadnych zbiorów pobranych i przetworzonych ręcznie przed wydarzeniem. Parametry upraw
(`crops.py`) i progi reguł (`analysis.py`) to stałe metodyczne opisane w kodzie.

## 6. Biblioteki, usługi zewnętrzne i narzędzia AI

**Usługi zewnętrzne (API):** ULDK, NMT WCS, BDOT10k WMS, ortofotomapa i granice działek (WMS) – GUGiK; Open-Meteo
(archiwum ERA5/ERA5-Land i prognozy); ISRIC SoilGrids REST; Earth Search STAC + AWS Open Data (Sentinel-2);
kafelki OpenStreetMap (podkład w widoku `/prosty/`).

**Modele i metody:** FAO-56 (Allen i in.) – ewapotranspiracja uprawy i bilans wody; SCS-CN (USDA NRCS, TR-55) – spływ powierzchniowy i wymiarowanie retencji na ulewę; Saxton & Rawls (2006) – pojemność
wodna gleby; priority-flood (Barnes i in. 2014) + D8 – spływ; prognoza zespołowa z danych historycznych – scenariusze.
Nie używamy modeli uczenia maszynowego ani modeli językowych do liczenia wyników; model językowy działa tylko w czacie i objaśnia gotowy raport.

**Narzędzia sztucznej inteligencji (zgodnie z pkt 5.1 i 5.3):**

| Narzędzie | Zakres i sposób użycia |
|---|---|
| Claude Code (Anthropic; modele Claude Opus i Sonnet) | asystent programisty podczas hackathonu: propozycje i generowanie części kodu, dokumentacji, testów i treści prezentacji; zespół przeglądał, uruchamiał i testował każdą zmianę. Warunki: komercyjne warunki usług Anthropic (wygenerowany kod należy do użytkownika). |
| ChatGPT (OpenAI), generowanie obrazów | zdjęcie rolnika z mapą pola (`web/public/img/rolnik-pole.jpg`) i animacja kiełkującego ziarna przy ładowaniu (`web/public/img/klos-ladowanie.gif`), wygenerowane przez zespół na podstawie opisów (promptów); obrazy przedstawiają postać fikcyjną. Warunki: OpenAI Terms of Use – prawa do wygenerowanych treści przysługują użytkownikowi, więc mogą zostać przeniesione na KOWR. |
| AI w działaniu aplikacji: asystent (czat) | model OpenAI (domyślnie `gpt-5.4-mini`, zmienna `WODNIK_CHAT_MODEL`) przez bibliotekę LangChain (`langchain-openai`). Dostaje opis raportu działki (bez geometrii, e-maila i danych konta) i pytania użytkownika; ma instrukcję, by podawać tylko liczby z raportu, mówić o niepewności i odsyłać do doradcy ODR. Wyników analizy (ryzyka, przyczyn, zaleceń) nie liczy AI, tylko jawne reguły. Warunki: OpenAI API Terms of Use (dane z API nie są domyślnie używane do trenowania modeli). Bez klucza czat działa bez AI. |

## 7. Licencje i warunki korzystania

**Dane:**

| Źródło | Licencja / warunki |
|---|---|
| GUGiK: ULDK, NMT, BDOT10k, ortofotomapa, KIEG | dane otwarte, bezpłatne (ustawa Prawo geodezyjne i kartograficzne, od 2020 r.) |
| Copernicus ERA5 / ERA5-Land, Sentinel-2 | licencja Copernicus: bezpłatna, także komercyjnie, z podaniem źródła |
| Open-Meteo | dane CC BY 4.0; **darmowe API do użytku niekomercyjnego** (prototyp); wdrożenie: plan komercyjny Open-Meteo albo pobieranie ERA5 bezpośrednio z Copernicus CDS (bezpłatnie) |
| ISRIC SoilGrids 2.0 | CC BY 4.0 |
| Earth Search (Element 84), AWS Open Data | publiczne, bez konta; dane na licencji Copernicus |
| OpenStreetMap (kafelki podkładu) | ODbL; kafelki OSM tylko do małego ruchu |

**Komponenty programowe:**

| Komponent | Licencja |
|---|---|
| numpy, scipy, rasterio (z GDAL: MIT), shapely | BSD-3-Clause |
| pyproj (z PROJ) | MIT |
| requests | Apache-2.0 |
| urllib3, fastapi, pydantic | MIT |
| uvicorn | BSD-3-Clause |
| React, react-dom, Vite, @vitejs/plugin-react | MIT |
| @react-pdf/renderer (PDF w aplikacji) | MIT |
| langchain-openai, langchain-core | MIT |
| openai (Python SDK) | Apache-2.0 |
| czcionka Inter (PDF w aplikacji) | SIL Open Font License 1.1 |
| Leaflet (widok `/prosty/`, z CDN unpkg) | BSD-2-Clause |

Wszystkie licencje pozwalają na przeniesienie praw do rozwiązania na KOWR i dalsze wykorzystanie (pkt 5.2 regulaminu).

## 8. Znane ograniczenia

Każdy raport zawiera listę ograniczeń dotyczących tej analizy. Ogólnie:

- **Czas analizy:** ponowna analiza działki < 1 s; pierwsza analiza nowej działki w testach 21.11.2026 trwała 8–31 s
  (5 regionów). Źródła pobieramy równolegle; najwolniejsze bywa szukanie zdjęcia Sentinel-2 bez chmur. Teren pobieramy
  z usługi NMT w formacie ASCII Grid, która od razu zwraca siatkę 2,5 m (3–8 s); usługa GeoTIFF 1 m jest tylko zapasowa,
  bo w testach potrafiła nie odpowiadać przez kilka minut. **Budżet czasu:** źródła opcjonalne (teren, rowy, gleba,
  satelita) mają łącznie 60 s (`WODNIK_SOURCE_BUDGET`); co nie zdąży, pomijamy w tym raporcie (opis w ograniczeniach)
  i pobieramy dalej w tle, więc ponowna analiza jest pełna. Pogoda jest wymagana. Przyspieszenie: patrz
  [skalowalność](#skalowalność-i-koszty-pkt-54--55).
- **Limit Open-Meteo:** darmowy plan ma dzienny limit zapytań; przy jego przekroczeniu serwer zwraca czytelny błąd
  `SOURCE_RATE_LIMITED`. Tło z 10 lat zużywa go ok. 3 razy mniej niż wcześniejsze 31 lat.
- **Pogoda z reanalizy** (siatka ok. 9–25 km): lokalne burze mogą dać inny opad.
- **Gleba z modelu SoilGrids** (250 m); docelowo mapa glebowo-rolnicza IUNG lub wyniki badań gleby rolnika.
- **Bilans FAO-56** zakłada pełne uwilgotnienie gleby 150 dni przed datą; Kc miesięczne (uproszczenie tabel FAO-56).
- **BDOT10k odczytujemy z obrazu mapy** (WMS), bo nie ma publicznej usługi zapytań wektorowych; dokładność odległości
  ok. ±2–4 m. Drenaż podziemny i stan urządzeń melioracyjnych nie są znane.
- **Satelita:** piksel 10–20 m; chmury mogą uniemożliwić analizę; zakresy NDVI dla upraw są orientacyjne (do kalibracji).
- **Bardzo duże działki** (bok > 2,5 km): analiza terenu obejmuje środkowy fragment; raport to zaznacza.
- **Progi reguł** (np. rok z deficytem: bilans 60 dni ≤ −100 mm) są heurystyczne, do kalibracji z metodyką IUNG.
- **Scenariusze 30 dni** zakładają pogodę podobną do ostatnich 10 lat; nie są prognozą konkretnej pogody.
- Serwer trzyma zadania w pamięci (restart je kasuje, poza działkami demo).

## 9. Weryfikacja wyników i rekomendacji

1. **Uzasadnienie przy każdym wniosku.** Każda pozycja raportu ma pole „Dlaczego” z liczbami i źródłem, a zalecenia
   z miejscem mają współrzędne. Rolnik lub doradca może je sprawdzić w terenie albo na mapie (`/prosty/`).
2. **Niezależne wskaźniki tej samej sytuacji.** Ocena łączy bilans FAO-56, klimatyczny bilans wodny, wilgotność gleby
   z ERA5-Land i stan roślin z Sentinel-2. Zgodność kilku wskaźników podnosi pewność, a rozbieżność ją obniża.
   Przykład Łazisko 15.06.2026: ujemny bilans 60-dniowy (−119 mm), wyczerpany zapas wody w strefie korzeni
   (66 z 106 mm, powyżej progu stresu) i spadek zieloności pszenicy o 0,17 w 3 tygodnie (Sentinel-2) wskazują to samo.
3. **Testy automatyczne** scenariuszy na syntetycznej pogodzie (`tests/test_scenarios.py`): suche lata dają stres
   w przewidywanym dniu (obliczenie ręczne), mokre lata – brak stresu, prognoza nadpisuje pierwsze dni.
4. **Kontrole na działkach testowych:** działka na Żuławach, obszarze gęstej sieci rowów (220907_5.0009.111) –
   wykryty rów melioracyjny BDOT10k na granicy działki, więc zalecenie zastawki; działka w Łazisku – brak rowów
   w BDOT10k w promieniu 500 m, więc zalecenie wału lub pasa zadarnionego zamiast zastawki. Położenie rowów można
   porównać z ortofotomapą w widoku `/prosty/`.
5. **Sprawdzenie na znanych latach suszy** (`walidacja/`): ta sama analiza na 15 czerwca dla 8 działek
   z 8 województw w latach 2015–2023. Porównujemy lata suszy wg IUNG-PIB (2015, 2018, 2019, 2022) z pozostałymi
   latami: jak często Wodnik wskazał ryzyko i ile dni stresu policzył. Wyniki: [walidacja/WYNIKI.md](walidacja/WYNIKI.md),
   dane: `walidacja/wyniki.csv`.

   **Wynik (72 analizy, 21.11.2026):** w latach suszy Wodnik częściej wskazuje ryzyko wysokie (66% wobec 55%), liczy
   więcej dni stresu (średnio 19 wobec 14 w ostatnich 30 dniach) i niższy bilans wody (−106 wobec −82 mm); najsilniej
   rok 2018 (wszystkie działki z ryzykiem wysokim). W 7 z 8 działek lata suszy mają więcej punktów ryzyka.
   **Kalibracja:** pierwsza wersja wskazywała ryzyko co najmniej umiarkowane prawie zawsze (92% także w pozostałych
   latach), bo w połowie czerwca bilans FAO-56 dla pszenicy niemal zawsze przekracza próg stresu (model nie uwzględnia
   podsiąku). Teraz taki poziom wymaga odchylenia od normy z ostatnich 10 lat (bilans, wilgotność gleby, stan roślin)
   albo wyczerpania ponad 80% wody. Wynik: 88% w latach suszy wobec 78% w pozostałych (wcześniej 97% wobec 92%).
   Zasada wynika z metody, a nie z dopasowania progów, ale sprawdzaliśmy ją na tych samych danych, więc to wynik
   optymistyczny. Odróżnianie lat jest umiarkowane: Wodnik dobrze porządkuje lata od suchszych do mokrszych, a progi
   poziomów wymagają dalszej kalibracji z danymi gminnymi IUNG.

   Jak uruchomić (pierwsze uruchomienie ok. 30–60 min, bo pobiera pogodę i zdjęcia dla 72 analiz; kolejne kilka sekund,
   bo dane są w pamięci podręcznej `.cache/`):

   ```bash
   .venv/bin/python walidacja/lata_suszy.py
   .venv/bin/python walidacja/podsumowanie.py
   ```

   Pierwszy skrypt zapisuje `walidacja/wyniki.csv`, drugi robi z niego tabelę `walidacja/WYNIKI.md`. Listę działek
   i lat zmienia się w `walidacja/lata_suszy.py` (`PARCELS`, `YEARS`, `DROUGHT_YEARS`). Uwaga: 72 analizy zużywają
   ok. 800 zapytań do darmowego Open-Meteo (dzienny limit to ok. 10 000).
6. **Do zrobienia:** porównanie z gminnymi danymi Systemu Monitoringu Suszy Rolniczej IUNG i kalibracja progów
   z ekspertami.

## Skalowalność i koszty (pkt 5.4 i 5.5)

- **Koszt dla rolnika: zero.** Podstawowe funkcje nie wymagają płatnych licencji ani instalacji.
- **Limity źródeł:** pamięć podręczna odpowiedzi (`.cache/`), zapis wyników (ta sama działka i data liczy się raz),
  zaokrąglenie punktu pogody do siatki 0,1° (sąsiednie działki dzielą dane), limit nowych analiz na adres IP
  (`WODNIK_RATE_LIMIT`, domyślnie 20/min), czytelne komunikaty o niedostępności źródeł.
- **Szybkość przy większym ruchu:** własna kopia ERA5 z Copernicus CDS (bez limitów), kafle NMT i BDOT10k/MPHP10k
  wczytane do własnej bazy przestrzennej (PostGIS) dla całej Polski – czas analizy spadnie do kilku sekund
  i zniknie zależność od wolnej usługi WCS; kolejka zadań (np. Redis) zamiast pamięci procesu.
- **Aktualizacja danych:** ERA5 codziennie (opóźnienie ok. 5 dni), Sentinel-2 co 2–5 dni (pobierany na żądanie),
  BDOT10k i NMT według cykli GUGiK (raz w roku wystarczy odświeżenie kopii).
- **Koszty infrastruktury (szacunek do weryfikacji):** prototyp działa na jednym małym serwerze;
  wersja krajowa: serwer aplikacji + baza PostGIS z NMT dla Polski (rzędu kilku TB danych) + opcjonalnie plan
  komercyjny Open-Meteo albo własne przetwarzanie ERA5.

## Bezpieczeństwo (pkt 5.6)

- Konto jest opcjonalne; jedyne dane osobowe to e-mail i opcjonalne imię. Hasła przechowujemy jako skrót
  PBKDF2-HMAC-SHA256 (200 000 iteracji, losowa sól), tokeny sesji tylko jako skrót SHA-256, ważne 30 dni.
  Użytkownik widzi i usuwa wyłącznie własne raporty. Limit prób logowania na adres IP.
- Asystent wysyła do OpenAI tylko treść pytań i opis raportu działki (bez e-maila i danych konta). Klucz API trzymamy
  w `.env` poza repozytorium. Limit pytań na adres IP.
- Baza kont `data/wodnik.db` jest poza repozytorium (`.gitignore`). Przy wdrożeniu: HTTPS, kopia zapasowa bazy,
  informacja RODO o przetwarzaniu e-maila.
- Walidacja wejścia (format numeru działki, zakres dat, lista upraw, współrzędne w granicach Polski).
- Limit nowych analiz na adres IP, ograniczenie liczby zadań w pamięci, limity czasu dla zewnętrznych usług.
- CORS ustawiany zmienną `WODNIK_CORS_ORIGIN`; brak kluczy i sekretów w repozytorium.

## Dokumentacja szczegółowa

| Dokument | Zawartość |
|---|---|
| [docs/ZGLOSZENIE.md](docs/ZGLOSZENIE.md) | opis zgłoszenia (problem, funkcje, dane, korzyści) i lista elementów do wysłania |
| [docs/ARCHITEKTURA.md](docs/ARCHITEKTURA.md) | struktura projektu, przepływ analizy, kontrakt danych |
| [docs/API.md](docs/API.md) | zapytania do serwera (endpointy, żądania, odpowiedzi, błędy) |
| [docs/UI.md](docs/UI.md) | strony interfejsu i zasady prostoty obsługi |
| [docs/RAPORT_AI.md](docs/RAPORT_AI.md) | projekt opcjonalnego raportu AI |
