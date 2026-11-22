# Zgłoszenie – HackNation 2026, zadanie KOWR

**Nazwa zespołu:** [nazwa zespołu – bez imion i nazwisk, zgodnie z regulaminem]
**Tytuł rozwiązania:** Wodnik – cyfrowy asystent wody na działce rolnej

## Zwięzły opis rozwiązania

**Problem.** Susza rolnicza wraca w Polsce coraz częściej, a dane, które pomagają jej przeciwdziałać (satelitarne,
meteorologiczne, glebowe, hydrologiczne, przestrzenne), są rozproszone i wymagają wiedzy specjalistycznej. Rolnik nie
dostaje odpowiedzi na proste pytania: czy na moim polu brakuje wody, dlaczego i co mogę zrobić – zanim sięgnę po
nawadnianie.

**Główne funkcjonalności.** Rolnik podaje numer działki ewidencyjnej (albo wskazuje ją na mapie), uprawę i datę.
Wodnik w kolejności wymaganej przez KOWR:
1. ocenia sytuację wodną: zapas wody w strefie korzeniowej, bilans opadu i parowania, wilgotność gleby i stan roślin
   z satelity (interpretowany dla wybranej uprawy), na tle 10 ostatnich lat; pokazuje też ryzyko na najbliższe 30 dni
   (scenariusze pogodowe z 10 lat),
2. wskazuje przyczyny niedoboru: pogoda, gleba albo odpływ wody z pola,
3. proponuje retencję w konkretnych miejscach działki (z kierunkiem i współrzędnymi): zastawka, gdy przy punkcie
   odpływu jest rów, wał lub pas zadarniony, gdy rowu nie ma, oczko w naturalnym obniżeniu, zadrzewienia,
4. dobiera działania agrotechniczne ograniczające straty wody,
5. na końcu ocenia, czy nawadnianie ma sens, kiedy i ile wody podać.

Raport zawiera datę, źródła danych, poziom pewności i ograniczenia; można go wydrukować lub zapisać jako PDF.

**Sposób wykorzystania danych.** Wszystkie dane są publiczne i pobierane na żądanie: granice działek (ULDK),
model terenu z LIDAR 1 m (NMT, GUGiK), rowy, cieki, zbiorniki, mokradła i lasy (BDOT10k), pogoda i wilgotność gleby
(ERA5/ERA5-Land), gleba (SoilGrids), zdjęcia Sentinel-2. Wynik liczy aplikacja metodami zgodnymi z materiałem
naukowym KOWR: bilans wody FAO-56, pojemność wodna gleby (Saxton & Rawls), analiza spływu po terenie, wskaźniki NDVI
i NDMI. Każdy wniosek ma uzasadnienie z konkretnymi liczbami.

**Najważniejsze korzyści.** Rolnik dostaje w jednym miejscu, bez znajomości GIS, konkretne i uzasadnione decyzje dla
swojego pola: gdzie zatrzymać wodę, co zmienić w uprawie i czy nawadnianie się opłaci. Retencja jest zawsze przed
nawadnianiem, co oszczędza wodę i pieniądze. Narzędzie jest darmowe dla rolnika i działa dla dowolnej działki
w Polsce; KOWR może je przejąć i rozwijać (otwarte licencje).

## Lista elementów zgłoszenia (pkt 4.1)

| Element | Gdzie | Stan |
|---|---|---|
| nazwa zespołu i tytuł | wyżej | ☐ uzupełnić nazwę zespołu |
| zwięzły opis | wyżej | ✔ |
| link do prywatnego repozytorium + dostęp dla jury | GitHub (Hack-The-Nation-2026) | ☐ sprawdzić prywatność, dodać konta jury wg instrukcji z platformy |
| dokumentacja README | [README.md](../README.md) (9 punktów z pkt 4.2) | ✔ |
| prezentacja PDF do 10 slajdów | pitch deck (eksport do PDF) | ☐ zaktualizować nazwę na Wodnik, dodać satelitę, hydrologię, scenariusze i zrzuty ekranu |
| działający prototyp + instrukcja uruchomienia | README pkt 1; demo online: <https://wodnik.vercel.app> (API: <https://wodnik-api.fastapicloud.dev>) | ✔ |
| film do 3 minut | [`video/out/prezentacja.mp4`](../video/out/prezentacja.mp4) — 2 min 55 s, 1920×1080, bez dźwięku | ✔ |
| wygenerowane raporty | `GET /api/v1/analyses/{id}/raport` → wydruk lub PDF | ☐ wygenerować 2–3 raporty dla różnych regionów i upraw |
