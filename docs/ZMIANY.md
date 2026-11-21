# Co się zmieniło (21.11.2026, po commicie „frontend3”)

Opis dla zespołu, głównie dla osoby od frontendu. **Grzegorz: zacznij od [grzegorz/README.md](../grzegorz/README.md)** (uruchomienie, konto, działki, Twoje zadanie). Zmiany są zrobione na aktualnym `main` (z „frontend3”).

**Uwaga: tym razem zmieniony jest `web/App.jsx`** (na prośbę zespołu: strona startowa z logowaniem, profil, wykresy
i asystent). Przed dalszą pracą nad frontendem zrób `git pull`, żeby nie było konfliktów. `styles.css` nie był ruszany;
nowe style są w osobnym `web/landing.css`.

## Co jest nowego we frontendzie (web/)

1. **Strona startowa z logowaniem** (`Landing.jsx`): opis projektu, problem w liczbach (ze źródłami), pitch
   („Rolnik zna swoje pole. My dokładamy dane.”), 5 kroków analizy, 5 źródeł danych, model biznesowy, plan wdrożenia,
   grafiki SVG i przykładowy raport. Po prawej logowanie / zakładanie konta, do tego „Wypróbuj bez konta”.
   Działa też na telefonie.
2. **Profil z historią raportów** (`Profile.jsx`): Otwórz (raport wraca do widoku wyniku), Drukuj, Usuń.
   W pasku u góry: „Imię · raporty” i „Wyloguj” albo „Zaloguj się” dla gościa.
3. **Wykresy w raporcie** (`Charts.jsx`, `charts.js`): „ten rok na tle 10 lat” w karcie „Bilans wodny” oraz karta
   „Jak doszło do tej sytuacji” (woda w glebie / opad i parowanie) nad scenariuszami. Kolory pod ciemny motyw
   ustawione w `landing.css` (zmienne `--chart-*`).
4. **Asystent** (`Chat.jsx`) pod tabelą zaleceń: podpowiedzi pytań, rozmowa o bieżącym raporcie.
5. **Poprawka błędu:** `handleRestart` („Od nowa”) był zdefiniowany poza komponentem `App`, więc kliknięcie
   kończyło się błędem. Teraz jest wewnątrz komponentu.

Zmiany w `App.jsx` są małe i opisane komentarzami: importy, stan konta (`user`, `guest`, `view`), przycisk
konta w pasku, przełącznik widoku profil / aplikacja, trzy komponenty w raporcie. Reszta Twojego kodu bez zmian.

Do zrobienia po stronie frontendu (jeśli chcesz):
- dopasować wygląd nowych ekranów do reszty, jeśli coś odstaje;
- **PDF:** `@react-pdf/renderer` nie pokaże wykresów; można dodać przycisk do raportu do druku z serwera
  (`/api/v1/analyses/{id}/raport`), który ma wszystkie trzy wykresy;
- fonty do PDF w `web/public/fonts/` i usunięcie z repo `web/.vite` (`git rm -r --cached web/.vite`).

Pozostałe zmienione pliki w `web/`: `api.js` (konto, historia, czat, pole `charts`; Twoja poprawka `uniqueSteps`
zachowana), `Scenarios.jsx` (tylko podpis okresu lat).

## Serwer i analiza

- **Asystent (czat)** (`api/chat.py`, `POST /api/v1/chat`): LangChain + OpenAI. Klucz `OPENAI_API_KEY` wpisz do
  pliku `.env` (wzór: `.env.example`; `.env` jest w `.gitignore`). Bez klucza czat działa w trybie podstawowym
  i zwraca skrót z raportu. Nowa zależność: `pip install -r requirements.txt` (`langchain-openai`).
- **Konta użytkowników** (`api/accounts.py`, SQLite w `data/wodnik.db`, poza repo): rejestracja, logowanie,
  wylogowanie, profil, historia raportów (lista, pełny raport, wydruk, usuwanie). Hasła jako skrót PBKDF2,
  tokeny ważne 30 dni, limit prób logowania. Endpointy: `docs/API.md` → „Konto i historia raportów”.
- **Dane do wykresów** w wyniku analizy (`report.charts`): opad, parowanie i zapas wody dzień po dniu
  z ostatnich ok. 150 dni oraz bilans z 60 dni w każdym z 10 poprzednich lat. Format: `docs/API.md`.
- **Raport do druku** (`/raport`) ma trzy wykresy w części „Ocena sytuacji wodnej” (`wodnik/charts.py`).
- **Hydrologia z BDOT10k** (`wodnik/hydrology.py`): rowy, cieki, zbiorniki, mokradła i lasy wokół działki.
  Zastawkę proponujemy tylko tam, gdzie przy punkcie odpływu jest rów; nowe zalecenia: retencja w rowach,
  zadrzewienia, ochrona mokradeł.
- **Satelita zależny od uprawy**: zieloność porównujemy z normą dla danej uprawy w danym miesiącu; dojrzewanie
  zbóż i pokos łąk nie są liczone jako susza. Doszły uprawy: pszenica jara, żyto.
- **Tło wieloletnie z 10 lat** przed datą analizy (wymóg zadania), także w scenariuszach na 30 dni.
- **Duże działki**: teren liczony w środkowym oknie zamiast odrzucenia działki.
- Zalecenia mają kierunek na działce (np. „na północnym krańcu”), więc nie powtarzają się tytuły.

## Widok /prosty (web-simple/)

Zapasowy, techniczny widok: dostał logowanie, listę „Moje raporty” i wykresy. Może służyć jako działający
przykład przy robieniu ekranów w React.

## Dokumentacja i testy

- `README.md`: punkty 1–9 z regulaminu, bezpieczeństwo (konta, RODO), testy.
- `docs/API.md`, `docs/UI.md`, `docs/ARCHITEKTURA.md`: zaktualizowane; nowy `docs/ZGLOSZENIE.md`
  (opis zgłoszenia i lista kontrolna).
- Testy: `tests/test_accounts.py`, `tests/test_charts.py`, `tests/test_chat.py` (nowe), `tests/test_scenarios.py`; wszystkie przechodzą.

## Demo przeliczone na prawdziwych danych

- `demo/lazisko_352_2026_06_15.json` (zamiast starego `lazisko_2026-06-15.json`, które usunęliśmy): ma scenariusze
  i dane do wykresów. ID zadania demo: `demo-lazisko_352_2026_06_15`.
- Wynik zmienił się z „wysokie” na **„umiarkowane”**: pszenica jest w stresie wodnym, ale tło to teraz 10 lat
  (wymóg zadania), a w 7 z 10 ostatnich lat bywało tu tak samo lub gorzej. Podsumowanie mówi to wprost.
- Slajd 6 prezentacji zaktualizowany do nowych liczb.

## Szybkość analizy (poprawione)

- W testach pięciu regionów nowa działka liczyła się 5–9 minut, bo usługa NMT GeoTIFF w GUGiK przestała odpowiadać
  (czekaliśmy do 3 × 180 s). Teraz teren pobieramy z usługi NMT ASCII Grid (EVRF2007), która zwraca od razu siatkę
  2,5 m w 3–8 s; GeoTIFF został jako zapas.
- **Budżet czasu 60 s** na źródła opcjonalne (teren, rowy, gleba, satelita): co nie zdąży, raport pomija i opisuje
  w ograniczeniach, a dane pobierają się w tle. Na liście postępu takie źródło ma stan `failed` (✖).
- Gleba: gdy SoilGrids nie ma danych w środku działki, bierzemy najbliższy sąsiedni piksel (250 m).
- Wynik po zmianach: nowe działki 8–31 s, powtórki poniżej 1 s.
- Poprawione teksty: „wschodnia część działki” (było „wschodnim część”), podsumowanie ryzyka nie pisze „gorzej niż
  zwykle”, gdy bilans jest typowy dla ostatnich lat, a przy wysokim ryzyku w scenariuszach dodaje ostrzeżenie.

## Nowość: „Co da retencja na tej działce”

- Nowa karta w raporcie (`web/WhatIf.jsx`, pod scenariuszami; w `App.jsx` jedna linijka) i sekcja w raporcie do druku.
- Liczy dla ulewy 30 i 50 mm (metoda SCS-CN, USDA): ile m³ wody spłynie z działki i z sąsiednich pól, ile metrów wału
  o wysokości 30 cm ją zatrzyma, ile zmieszczą naturalne obniżenia (oczko) oraz ile wody więcej zmieści gleba
  z większą ilością materii organicznej. Przykład, Łazisko: ulewa 50 mm → ok. 1026 m³, ok. 433 m wału, obniżenia
  mieszczą 76%, materia organiczna +5 mm.
- Uczciwie opisane: na dobowych danych ERA5 nie widać lokalnych ulew, więc nie liczymy spływu z historii pogody,
  tylko wymiarujemy działania na przykładową ulewę.
- Asystent (czat) zna te wyniki i może o nie pytać rolnik.
- Demo przeliczone; zlewnia Łaziska wychodzi teraz 8,0 ha (nowa usługa NMT, siatka 2,5 m), a w raporcie doszło
  oczko w naturalnym obniżeniu. Slajd 6 zaktualizowany.

## Walidacja na latach suszy i kalibracja ryzyka

- Nowy katalog `walidacja/`: 72 analizy (8 działek z 8 województw, 15 czerwca 2015–2023) porównujące lata suszy wg IUNG
  (2015, 2018, 2019, 2022) z pozostałymi. Wyniki: `walidacja/WYNIKI.md`, uruchamianie: README, punkt 9.
- Kalibracja: poziom ryzyka „umiarkowane” lub „wysokie” wymaga teraz odchylenia od normy z ostatnich 10 lat
  (bilans, wilgotność gleby, stan roślin) albo wyczerpania ponad 80% wody w strefie korzeni. Sam stres w bilansie
  daje „niskie” z podsumowaniem „niedobór typowy dla tego terminu”. W wyniku jest nowe pole
  `raw.ryzyko_skladniki` (punkty za stres, za odchylenie od normy i za okres krytyczny).
- Efekt: ryzyko co najmniej umiarkowane w latach suszy 88%, w pozostałych 78% (wcześniej 97% i 92%); demo Łaziska
  bez zmian (umiarkowane).

## Wygląd: zdjęcie, animacja ładowania, cieplejsze teksty

- Strona startowa: w hero zamiast abstrakcyjnej grafiki jest podgląd prawdziwego raportu, a w sekcji „Rolnik zna swoje
  pole” zdjęcie rolnika z mapą działki (`web/public/img/rolnik-pole.jpg`, zmniejszona kopia oryginału PNG).
- Ładowanie analizy: animacja kiełkującego ziarna (`web/public/img/klos-ladowanie.gif`) nad listą postępu.
- `App.jsx`: pasek kroków (Twoje pole → Uprawa i data → Raport i rady), powitanie zalogowanego, cieplejsze teksty
  („Gdzie jest Twoje pole?”, „Co rośnie na tym polu?”, „Twój raport”, „W skrócie”), kolor plakietki ryzyka zależny
  od poziomu, stopka. Czcionka Inter wczytywana z Google Fonts (`index.html`). Pasek górny mieści się na telefonie.
- Asystent: odpowiedzi z pogrubieniami i listami wyświetlane czytelnie (bez surowych `**`), zwraca się na „Ty”.
- Oryginały plików z polskimi nazwami w `web/public/img/` zostały nieruszone; strona używa kopii `rolnik-pole.jpg`
  i `klos-ladowanie.gif`. Oryginały można usunąć.

