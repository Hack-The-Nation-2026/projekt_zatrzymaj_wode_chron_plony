# Dla Grzegorza: start w 5 minut

## Twoje zadanie: bardziej ludzki asystent

Pod każdym raportem jest czat „Zapytaj asystenta o ten raport”. Działa, ale odpowiada jeszcze trochę jak urzędnik.
Cel: żeby brzmiał jak życzliwy doradca rolniczy, który szanuje wiedzę rolnika.

Gdzie to zmieniać:
- `api/chat.py`: `SYSTEM_PROMPT` (charakter i zasady asystenta), `report_context()` (co asystent wie o raporcie),
  `_fallback()` (odpowiedź, gdy nie ma klucza AI);
- `web/Chat.jsx`: wygląd czatu i podpowiedzi pytań (`SUGGESTIONS`).

Pomysły na start: krótsze odpowiedzi, jedno pytanie zwrotne zamiast listy, nawiązanie do uprawy i miesiąca,
mniej żargonu („zapas wody w glebie” zamiast „wyczerpanie Dr”), ciepłe powitanie po otwarciu raportu.
Zasady, których nie ruszamy: liczby tylko z raportu, retencja przed nawadnianiem, odesłanie do ODR przy rowach i stawach.

## Uruchomienie

W katalogu projektu, raz:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
cd web && npm install && npm run build && cd ..
```

Klucz do AI: skopiuj `.env.example` do `.env` i wpisz `OPENAI_API_KEY` (poproś Maćka albo użyj swojego).
Bez klucza czat działa w trybie podstawowym.

Konto testowe (zakłada je w Twojej lokalnej bazie, z jednym gotowym raportem w historii):

```bash
.venv/bin/python grzegorz/utworz_konto.py
```

Start serwera:

```bash
.venv/bin/uvicorn api.main:app --port 8000
```

Otwórz <http://localhost:8000>. Po zmianie w `api/` zrestartuj serwer (Ctrl+C i ponownie). Po zmianie w `web/`
uruchom `npm run build` w `web/` albo pracuj na `npm run dev` (adres <http://localhost:5173>).

## Konto

- e-mail: `grzegorz@wodnik.test`
- hasło: `wodnik-grzegorz-2026`

To konto tylko do testów, w lokalnej bazie `data/wodnik.db` (nie trafia do repozytorium).

## Przykładowe działki

Te działki mają już policzone dane, więc wynik pojawi się szybko (wpisz podaną datę i uprawę):

| Działka | Gdzie | Data | Uprawa |
|---|---|---|---|
| `101609_2.0011.352` | Łazisko, łódzkie (demo) | 15.06.2026 | pszenica ozima |
| `040704_2.0037.90/2` | pod Inowrocławiem | 15.07.2025 | burak cukrowy |
| `060408_2.0139.1051/2` | pod Hrubieszowem | 20.05.2024 | pszenica ozima |
| `201310_2.0004.1034/2` | pod Wysokiem Mazowieckiem | 10.07.2023 | trwałe użytki zielone |
| `161002_5.0050.597` | pod Głogówkiem | 15.05.2026 | rzepak ozimy |

Uwaga: dane w pamięci podręcznej (`.cache/`) są tylko na komputerze Maćka. U Ciebie pierwsze liczenie każdej
działki potrwa 10–60 s, demo Łaziska działa od razu.

## Jak się poruszać

1. **Strona startowa** (`/`): opis projektu i logowanie. „Wypróbuj bez konta” pomija logowanie.
2. **Krok 1 „Gdzie jest Twoje pole?”**: numer działki albo „Wybierz na mapie”. Link „Zobacz przykładowe pole
   w Łazisku” wypełnia wszystko sam.
3. **Krok 2 „Co rośnie na tym polu?”**: uprawa i data, potem „Zatwierdź wybór”.
4. **Krok 3 „Twój raport”**: wykresy, scenariusze na 30 dni, „Co da retencja”, zalecenia, a na dole **czat**.
5. **Profil**: przycisk „Imię · raporty” u góry. Historia raportów: Otwórz, Drukuj, Usuń.

Przydatne adresy: `/prosty/` (prosty widok z mapą), `/docs` (wszystkie zapytania API),
`/api/v1/analyses/demo-lazisko_352_2026_06_15/raport` (raport do druku).

## Projekty wyglądu

W `grzegorz/projekty/` są cztery warianty strony do otwarcia w przeglądarce (dwuklik na plik):
A granat i zboże, B jasny len i zieleń, C ziemia i woda, D telefon (ładowanie i raport).
Używają naszego zdjęcia i animacji z `web/public/img/`. Wersja edytowalna jest na płótnie w Claude
(link u Maćka; trzeba go Ci udostępnić).
