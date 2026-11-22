# Film Wodnika

Film na wyzwanie KOWR „Zatrzymaj wodę, chroń plony”, 2 min 55 s, 1920×1080,
30 klatek na sekundę, bez dźwięku. Komentarz (lektor) dogrywamy osobno.

Gotowy plik leży w `out/prezentacja.mp4`. Scenariusz i kolejność ujęć:
`../docs/SCENARIUSZ_FILMU.md`.

## Jak to powstaje

Film składa się z prawdziwych nagrań działającej aplikacji. Całość powstaje
w trzech krokach.

1. `scripts/record.mjs` uruchamia Chrome przez Playwrighta, wstrzykuje kursor
   i przechodzi przez Wodnika, zapisując każdy rozdział jako osobny plik w
   `public/clips/`. Chrome nagrywa WebM, więc każdy plik od razu przechodzi
   przez ffmpeg na H.264, który render dekoduje lżej. Przy okazji powstaje
   tabela znaczników (`out/marks-*.json`) z czasami zdarzeń, takich jak
   pokazanie wyniku albo odpowiedź asystenta.
2. `scripts/plan.mjs` czyta te znaczniki i opisuje montaż, czyli które fragmenty
   nagrań wchodzą do filmu, jak szybko i gdzie w tym czasie patrzy kamera.
   Wynik zapisuje do `src/edl.ts`.
3. `src/` to projekt Remotiona, który składa nagrania w jedną całość, dokłada
   ruch kamery, polskie napisy na dole kadru i wyciemnienie na początku. Na końcu
   stoi karta z adresem demo i kodem QR (`src/components/OutroScene.tsx`), więc
   film da się obejrzeć bez przepisywania adresu ze slajdu.

Napisy na dole to zdania lektora: część jury ogląda film bez dźwięku, więc treść
musi być czytelna także wtedy.

## Nagrania

`record.mjs` przyjmuje nazwę rozdziału albo `all`.

```bash
node scripts/record.mjs all       # wszystko po kolei
node scripts/record.mjs 03-analiza
node scripts/record.mjs ladowanie # nie ma takiego rozdziału, szukaj po nazwie z listy niżej
```

Rozdziały to `01-start` (strona startowa: problem, pitch, kroki KOWR, dane,
model), `02-logowanie` (logowanie i powitanie w aplikacji), `03-analiza`
(numer działki, uprawa i data, ekran sprawdzania, wynik z bilansem wodnym),
`04-wykresy` („Jak doszło do tej sytuacji?”: woda w glebie, opad i parowanie),
`05-scenariusze` (najbliższe 30 dni), `06-retencja` („Co da retencja na tej
działce”), `07-zalecenia` (tabela ścieżki KOWR), `08-asystent` (czat z AI),
`09-druk` (stopka raportu), `10-wydruk` (raport do wydruku), `11-profil`
(historia raportów) i `12-powrot` (wylogowanie i strona startowa).

Nagrania wymagają serwera na `:8000`. Wodnik podaje tam zbudowany frontend
(`web/dist/`), więc film pokazuje dokładnie to, co zobaczy jury:

```bash
cd .. && .venv/bin/uvicorn api.main:app --port 8000
```

`record.mjs` zakłada konto `film@wodnik.test` (hasło `wodnik-film-2026`, imię
Grzegorz) i zapisuje stan zalogowania do `public/clips/state-login.json`, więc
rozdziały inne niż samo logowanie startują od razu na kroku 1. Stan jest
tworzony na nowo przy każdym uruchomieniu.

Działka demo to `101609_2.0011.352`, data 15.06.2026, pszenica ozima. Wynik dla
tego zestawu leży gotowy w `demo/`, więc po „Zatwierdź wybór” raport pojawia się
od razu.

## Dwie rzeczy, które warto wiedzieć

**Ekran sprawdzania.** Wynik demo liczy się natychmiast, więc prawdziwy ekran
„Sprawdzamy Twoje pole…” z listą etapów mrugnąłby tylko jednym kadrem. W rozdziale
`03-analiza` `scripts/app.mjs` (`stageLoading`) podstawia odpowiedź serwera na stan
`running` i rozkłada etapy w czasie. Podmieniamy wyłącznie stan zadania — etykiety
etapów, animacja kłosu i cały raport są prawdziwe. Dzięki temu w kadrze jest
prawdziwy postęp analizy, a nie jego atrapa.

**Pobieranie PDF.** `GET /analyses/{id}/raport.pdf` na tej maszynie zwraca 500,
więc w filmie pokazujemy przycisk „Drukuj” i raport do wydruku (rozdział
`10-wydruk`, otwierany bezpośrednio z `/analyses/demo-lazisko_352_2026_06_15/raport`).
Scenariusz dopuszcza to rozwiązanie.

## Pomiar i zrzuty kontrolne

`scripts/measure.mjs` przechodzi przez aplikację i wypisuje środki i ramki sekcji
oraz wykresów. Z tych liczb korzysta kamera w `plan.mjs`, żeby zbliżenie objęło
treść, a nie tło.

`scripts/shots.mjs` zapisuje zrzuty najważniejszych ekranów do `out/check/`
i odświeża stan zalogowania. Służy do sprawdzenia kadru bez renderowania filmu.

## Render

```bash
npm install
node scripts/record.mjs all
node scripts/plan.mjs
npx remotion render src/index.ts Wodnik out/prezentacja.mp4 --codec h264 --crf 20
```

Podgląd na żywo uruchamia `npx remotion studio src/index.ts`. Klatkę kontrolną
robimy przez `npx remotion still src/index.ts Wodnik out/still.png --frame 2120`.

Krój pisma jest wpięty z `public/fonts/` (IBM Plex Sans, zakres łaciński
i rozszerzony), więc render nie sięga do sieci.

Kod QR (`public/qr-wodnik.png`) prowadzi na `https://wodnik.vercel.app` i jest
zapisany w repozytorium, żeby render nie zależał od żadnej usługi zewnętrznej.
Odczyt kodu sprawdzimy w każdej chwili: `zbarimg -q public/qr-wodnik.png`.

## Znaczniki czasu dla lektora

Lektor nagrywa się do gotowego obrazu, więc poniżej rozkład scen w finalnym
montażu (sekwencja 5240 klatek, 174,7 s). Czas podany od początku filmu.

| Scena | Od | Do | Napis w kadrze |
|---|---|---|---|
| hero | 0:00,0 | 0:08,4 | Susza to już nie wyjątek… |
| liczby | 0:08,4 | 0:13,2 | Polska zatrzymuje tylko 7,5% wody… |
| pitch | 0:13,2 | 0:17,5 | Rolnik zna swoje pole… |
| kroki | 0:17,5 | 0:22,6 | Ocena, przyczyny, retencja, agrotechnika… |
| zrodla | 0:22,6 | 0:27,5 | GUGiK, BDOT10k, ERA5, Sentinel-2, SoilGrids… |
| model | 0:27,5 | 0:34,4 | Dla rolnika za darmo… |
| konto | 0:34,4 | 0:39,2 | Konto jest opcjonalne… |
| logowanie | 0:39,2 | 0:52,4 | Zakładamy konto albo logujemy się od razu… |
| krok1 | 0:52,4 | 0:58,9 | Wystarczy numer działki z ewidencji… |
| uprawa | 0:58,9 | 1:03,8 | Wybieramy uprawę i datę… |
| ladowanie | 1:03,8 | 1:08,3 | Wodnik pobiera równolegle granice działki… |
| raport | 1:08,3 | 1:12,4 | Pszenica jest już w stresie wodnym… |
| przyczyny | 1:12,4 | 1:15,0 | Lekka, piaszczysta gleba słabo trzyma wodę… |
| bilans | 1:15,0 | 1:18,1 | Wykres pokazuje dziesięć lat tła… |
| woda | 1:18,1 | 1:22,8 | Widać, kiedy zapas wody spadł poniżej progu… |
| opad | 1:22,8 | 1:26,9 | Opad nie nadążał za parowaniem… |
| scenariusze | 1:26,9 | 1:31,2 | Dziesięć scenariuszy pogody… |
| scen-wykres | 1:31,2 | 1:36,3 | Pasmo pokazuje rozrzut od suchych do mokich lat… |
| retencja | 1:36,3 | 1:40,5 | Przy ulewie 50 mm spłynie ponad tysiąc m³… |
| ulewy | 1:40,5 | 1:44,2 | Dla 30 mm to 193 m³, dla 50 mm — 1026 m³. |
| srodki | 1:44,2 | 1:50,0 | Około 430 metrów wału, 781 m³ w oczku, +5 mm… |
| tabela | 1:50,0 | 1:54,8 | Każda rada ma miejsce, uzasadnienie i pewność… |
| agro | 1:54,8 | 1:58,9 | Międzyplony, resztki pożniwne… |
| czat-pytanie1 | 1:58,9 | 2:03,9 | Rolnik może po prostu zapytać… |
| czat-odpowiedz1 | 2:03,9 | 2:11,3 | Odpowiada prostym językiem… |
| czat-pytanie2 | 2:11,3 | 2:15,3 | Pyta też o formalności… |
| czat-odpowiedz2 | 2:15,3 | 2:20,4 | Przy rowach, stawach i poborze wody odsyła do ODR… |
| druk | 2:20,4 | 2:24,3 | Raport można wydrukować dla doradcy… |
| wydruk-gora | 2:24,3 | 2:29,7 | Jedna strona: ocena, przyczyny, liczby, mapa. |
| wydruk-wykresy | 2:29,7 | 2:33,3 | Wszystkie wykresy trafiają też na wydruk. |
| wydruk-lata | 2:33,3 | 2:35,9 | Ten rok na tle poprzednich lat… |
| profil | 2:35,9 | 2:39,7 | Konto zapisuje historię raportów. |
| historia | 2:39,7 | 2:44,6 | Każdą analizę można otworzyć, wydrukować, usunąć. |
| powrot | 2:44,6 | 2:49,7 | Zatrzymaj wodę, chroń plony. |
| outro | 2:49,7 | 2:54,7 | (karta z kodem QR) |

Napisy są widoczne na dole każdej sceny, więc lektor może czytać dokładnie to,
co pokazuje kadr.

Nagrania, klatki kontrolne i zrzuty ekranu nie trafiają do repozytorium (patrz
`.gitignore` w tym katalogu). Do repozytorium wchodzi sam projekt filmu i gotowy
`out/prezentacja.mp4`. Nagrania odtwarzają się skryptami z `scripts/`.
