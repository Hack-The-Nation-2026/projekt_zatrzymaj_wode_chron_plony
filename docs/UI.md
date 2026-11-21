# Interfejs użytkownika: strony i makiety

Kryterium „prostota obsługi” (15%) mówi o użytkowniku **bez przygotowania technicznego** i o **warunkach pracy w gospodarstwie**. Stąd zasady poniżej.

## Zasady

- **Telefon najpierw.** Rolnik używa tego w polu: duże przyciski (min. 48 px), czytelny kontrast na słońcu, jedna kolumna.
- **Trzy pola wejścia i jeden przycisk:** działka, data, uprawa.
- **Język rolnika, nie hydrologa.** „Woda szybko ucieka z pola”, a nie „skoncentrowany spływ powierzchniowy”. Terminy techniczne tylko w „Dlaczego?”.
- **Wynik w 10 sekund:** poziom ryzyka, główna przyczyna, 3 najważniejsze działania. Szczegóły dopiero po rozwinięciu.
- **Kolor nigdy sam:** ryzyko zawsze ma też słowo i ikonę („Wysokie”), bo część użytkowników nie rozróżnia kolorów.
- **Ścieżka KOWR widoczna jako 5 kroków** (stepper). To dokładnie ta sekwencja, którą ocenia jury, więc nie chowamy jej.
- **Uczciwość:** pewność i ograniczenia są widoczne przy każdej radzie, nie na dole małym drukiem.

## Mapa stron

```
 [1 Start] → [2 Analiza] → [3 Wynik] ─┬→ [4 Mapa działań]
   wybór       postęp        podsumowanie│→ [5 Dlaczego?] dane, wykres, pewność
   działki                                └→ [6 Raport] AI + druk / PDF
                                  [7 O metodzie] źródła, licencje, ograniczenia (stopka)
```

## 1. Start: wybór działki

Cel: wskazać działkę na trzy sposoby, bez wpisywania czegokolwiek długiego.

```
┌────────────────────────────────────────┐
│ 💧 Wodnik                    [O metodzie]│
├────────────────────────────────────────┤
│ Sprawdź wodę na swojej działce          │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │            MAPA (ortofoto)          │ │
│ │       dotknij swoje pole  ◉         │ │
│ │   ┌──────┐ zaznaczona działka       │ │
│ │   │      │ Łazisko 352 · 3,01 ha    │ │
│ │   └──────┘                          │ │
│ └─────────────────────────────────────┘ │
│  📍 Użyj mojej lokalizacji              │
│  🔎 Wpisz numer działki: [__________]   │
│                                         │
│  Data:   [ dziś ▾ ]                     │
│  Uprawa: [ pszenica ozima ▾ ]           │
│                                         │
│  [        SPRAWDŹ WODĘ        ]         │
└────────────────────────────────────────┘
```

Zachowanie:
- Dotknięcie mapy → `GET /parcels/resolve` → podświetlona działka z nazwą i powierzchnią.
- „Moja lokalizacja” → geolokalizacja przeglądarki → ten sam endpoint.
- Wpisanie numeru → `GET /parcels/search`. Przy braku wyniku komunikat: „Nie znaleziono działki. Dotknij jej na mapie.”
- Data domyślnie „dziś”, można cofnąć (do analizy po fakcie, np. susza z zeszłego roku).
- Uprawa: lista 7 pozycji + „nie wiem / odłóg” (wtedy użytki zielone jako zamiennik z informacją).
- Przycisk nieaktywny, dopóki nie ma działki.
- **Przykłady demo:** trzy przyciski „Wypróbuj na przykładowej działce”, ładujące gotowy wynik z `demo/` (działa bez internetu).

## 2. Analiza: postęp

Pierwsze przeliczenie trwa kilkadziesiąt sekund, więc użytkownik musi widzieć, że coś się dzieje i co.

```
 Sprawdzam Twoją działkę…
 ✔ Granice działki
 ✔ Pogoda z ostatnich miesięcy
 ◔ Gleba…
 ○ Ukształtowanie terenu
 ○ Wnioski i zalecenia
```

Źródłem są etapy zadania z API (`GET /analyses/{id}` → `progress`). Przy błędzie jednego źródła analiza idzie dalej, a wynik ma obniżoną pewność i komunikat, czego zabrakło.

## 3. Wynik: podsumowanie

Najważniejszy ekran, zbudowany z góry na dół:

```
┌────────────────────────────────────────┐
│ ← Łazisko 352 · 3,01 ha · 15.06.2026    │
│   pszenica ozima                        │
├────────────────────────────────────────┤
│  ⚠ RYZYKO SUSZY: UMIARKOWANE            │
│  Zapas wody się kurczy; warto działać   │
│  zanim pojawi się wyraźny stres.        │
│  Pewność analizy: średnia ⓘ             │
├────────────────────────────────────────┤
│ Główna przyczyna                        │
│  🪨 Gleba słabo magazynuje wodę         │
│     (lekka, piaszczysta)                │
│  ↳ także: woda ucieka z pola (umiark.)  │
├────────────────────────────────────────┤
│ Co zrobić najpierw                      │
│  1 Zatrzymaj wodę w miejscu odpływu 📍  │
│  2 Dodaj międzyplon po zbiorze          │
│  3 Nawadnianie: tylko jeśli masz        │
│    instalację (okres krytyczny)         │
├────────────────────────────────────────┤
│ [Zobacz na mapie] [Dlaczego?] [Raport]  │
└────────────────────────────────────────┘
```

Pod spodem **stepper 5 kroków** (Ocena · Przyczyny · Retencja · Agrotechnika · Nawadnianie). Każdy krok rozwija się w listę kart. Karta rekomendacji:

```
┌────────────────────────────────────────┐
│ Zatrzymaj wodę w miejscu odpływu    📍  │
│ Woda opuszcza działkę w tym punkcie.   │
│ Jeśli jest tu rów: zastawka lub próg…  │
│ Pewność: średnia   ▸ Dlaczego tak?     │
└────────────────────────────────────────┘
```

- „Dlaczego tak?” rozwija pole `because` (liczby i źródła).
- Ikona 📍 przenosi na mapę do konkretnego miejsca.
- Nawadnianie ma zawsze wizualnie najniższy priorytet (szare tło, etykieta „dopiero na końcu”), zgodnie z wytycznymi KOWR.

## 4. Mapa działań

Pełnoekranowa mapa z warstwami do włączania:

| Warstwa | Źródło w odpowiedzi API |
|---|---|
| granica działki | `parcel.geometria_wgs84` |
| punkty odpływu (zastawki, wały) | `retention[].location` (rodzaj „odpływ”) |
| zagłębienia (oczka, mokradła) | `retention[].location` (rodzaj „zagłębienie”) |
| linie spływu | `layers.flow_lines` **[do dodania]** |
| dopływ z sąsiednich pól | `layers.inflow` **[do dodania]** |

Dotknięcie znacznika otwiera tę samą kartę rekomendacji co w wyniku. Przycisk „Otwórz w mapach” używa linku z `location.maps` (nawigacja w teren).

## 5. Dlaczego? (dane i wiarygodność)

Dla doradców i jury. Jeden wykres plus tabela.

```
 Zapas wody w glebie (mm)
 ┌──────────────────────────────────────┐
 │ TAW ─────────────────────────────    │
 │ próg stresu ┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈     │
 │          ╱╲    ╱▔▔╲___╱▔╲            │
 │  ▁▁▂▃▄▅▆╱  ╲__╱         ╲▁           │
 │ sty        kwi        cze            │
 └──────────────────────────────────────┘
 ▮ opady (słupki u dołu)
```

Pod wykresem:
- 4 wskaźniki oceny z percentylem w tle 31 lat („tak sucho było w 16% lat”),
- tabela źródeł: nazwa, co daje, **czy dane były z internetu czy z cache**, data pobrania,
- lista ograniczeń (`uncertainty`) i co poprawi pewność (np. „wpisz typ gleby z badania”).

## 6. Raport (AI + druk)

Generowanie opisu w języku rolnika z gotowego wyniku. Szczegóły i zabezpieczenia: [RAPORT_AI.md](RAPORT_AI.md).

```
┌────────────────────────────────────────┐
│ Raport dla gospodarstwa                 │
│ [ Wygeneruj opis prostym językiem ]     │
│                                         │
│ ┌ Wygenerowano przez AI na podstawie ─┐ │
│ │ wyników analizy. Sprawdź zalecenia. │ │
│ ├─────────────────────────────────────┤ │
│ │ Podsumowanie… Co robić najpierw… … │ │
│ └─────────────────────────────────────┘ │
│ [Drukuj / PDF] [Kopiuj tekst] [Edytuj]  │
└────────────────────────────────────────┘
```

- Raport zawsze działa też **bez AI**: gdy usługa nie odpowiada, pokazujemy szablonowy tekst z `output.text()`.
- Widoczna etykieta „napisane przez AI” i data wygenerowania.
- Wersja do druku (A4, jedna strona) do dołączenia do wniosku lub rozmowy z doradcą.

## 7. O metodzie

Statyczna strona w stopce: kolejność KOWR, metody (FAO-56, SoilGrids, NMT), tabela źródeł z licencjami, ograniczenia. To odpowiada wymogowi transparentności z regulaminu i kryterium wiarygodności.

## Stany pomocnicze

| Stan | Co pokazujemy |
|---|---|
| brak internetu | baner „Tryb offline: dostępne tylko przykładowe działki” |
| działka za duża (> 2,2 km) | „Działka jest za duża dla prototypu. Wybierz mniejszą część.” |
| źródło danych nie odpowiada | wynik z obniżoną pewnością + lista, czego brakuje |
| data bez wilgotności gleby (ostatnie ~6 dni) | wskaźnik oznaczony „brak danych”, pozostałe działają |
| działka miejska / woda | „Dla tego miejsca brak danych glebowych. Wskaż pole uprawne.” |

## Dostępność i język

- Interfejs po polsku, liczby z przecinkiem dziesiętnym (zgodnie z `num()` w rdzeniu).
- Kontrast tekstu min. 4,5:1, `aria-label` na ikonach, obsługa klawiatury.
- Opcjonalnie później: duży krój pisma i tryb „uproszczony” (tylko ekran 3).

## Kolejność budowy (dla hackathonu)

1. Ekran 1 + 3 (wybór działki → wynik) na danych z `demo/`: to już daje demo.
2. Podłączenie API (ekran 2).
3. Mapa działań (4).
4. Raport AI (6).
5. „Dlaczego?” z wykresem (5) i „O metodzie” (7).
