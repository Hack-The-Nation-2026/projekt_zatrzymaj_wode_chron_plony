export type CameraKey = {
  /** Czas w sekundach od początku sceny. */
  t: number
  /** Powiększenie kadru. 1 = całe nagranie. */
  z: number
  /** Punkt, na którym trzyma się kamera, we współrzędnych nagrania 1920×1080. */
  x: number
  y: number
}

export type Scene = {
  id: string
  /** Plik nagrania bez rozszerzenia, z katalogu public/clips. Nie ma go karta końcowa. */
  clip?: string
  /** Początek i koniec wycinka w nagraniu, w sekundach. */
  from: number
  to: number
  /** Przyspieszenie nagrania. 1 = normalnie, mniej niż 1 = zwolnienie. */
  rate?: number
  /** Tylko karta końcowa nie ma nagrania. */
  kind?: 'screen' | 'outro'
  /** Etykieta nad zdaniem lektora i samo zdanie: napisy dla jury bez dźwięku. */
  title?: string
  caption?: string
  camera?: CameraKey[]
}

/** Montaż: kolejność rozdziałów, wycinki z nagrań i ruch kamery. */
export const scenes: Scene[] = [
  {
    id: 'hero',
    clip: '01-start',
    from: 1.1,
    to: 8.2,
    rate: 0.85,
    title: "Wodnik",
    caption: "Susza to już nie wyjątek, tylko codzienność polskiego rolnictwa. Za każdą płacimy po fakcie — miliardami złotych pomocy.",
    // 8.35s
    camera: [
      { t: 0, z: 1, x: 960, y: 540 },
      { t: 3, z: 1.05, x: 860, y: 500 },
      { t: 7, z: 1.03, x: 900, y: 520 },
    ],
  },
  {
    id: 'liczby',
    clip: '01-start',
    from: 8.4,
    to: 13,
    rate: 0.95,
    title: "Problem",
    caption: "Polska zatrzymuje tylko 7,5 procent wody, która przez nią przepływa. Za susze 2018–2019 zapłaciliśmy 4,36 mld zł.",
    // 4.84s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 420 },
      { t: 2, z: 1.08, x: 880, y: 430 },
      { t: 4.6, z: 1.04, x: 950, y: 440 },
    ],
  },
  {
    id: 'pitch',
    clip: '01-start',
    from: 13.2,
    to: 17.3,
    rate: 0.95,
    title: "Dlaczego Wodnik",
    caption: "Rolnik zna swoje pole. Łączenie zdjęć satelitarnych, modeli terenu i pogody z dziesięciu lat bierzemy na siebie.",
    // 4.32s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 460 },
      { t: 1.6, z: 1.08, x: 1000, y: 460 },
      { t: 3.6, z: 1.04, x: 1060, y: 470 },
    ],
  },
  {
    id: 'kroki',
    clip: '01-start',
    from: 17.4,
    to: 22.2,
    rate: 0.95,
    title: "Kolejność KOWR",
    caption: "Ocena, przyczyny, retencja, agrotechnika — a nawadnianie na końcu. Dokładnie w tej kolejności.",
    // 5.05s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 390 },
      { t: 2, z: 1.07, x: 960, y: 400 },
      { t: 4.4, z: 1.03, x: 960, y: 420 },
    ],
  },
  {
    id: 'zrodla',
    clip: '01-start',
    from: 22.3,
    to: 27,
    rate: 0.95,
    title: "Pięć źródeł danych",
    caption: "GUGiK, BDOT10k, Copernicus ERA5, Sentinel-2 i SoilGrids. Dane publiczne, liczone od nowa dla każdej działki.",
    // 4.95s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 390 },
      { t: 2, z: 1.07, x: 960, y: 420 },
      { t: 4.4, z: 1.03, x: 960, y: 440 },
    ],
  },
  {
    id: 'model',
    clip: '01-start',
    from: 27,
    to: 33.6,
    rate: 0.95,
    title: "Model biznesowy",
    caption: "Dla rolnika za darmo. Kanałem są KOWR i ośrodki doradztwa, a wartość dla państwa to mniej strat po suszy.",
    // 6.95s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 400 },
      { t: 2.4, z: 1.06, x: 960, y: 480 },
      { t: 4.8, z: 1.06, x: 960, y: 560 },
      { t: 6.4, z: 1.03, x: 960, y: 600 },
    ],
  },
  {
    id: 'konto',
    clip: '01-start',
    from: 33.6,
    to: 37.9,
    rate: 0.9,
    title: "Konto",
    caption: "Konto jest opcjonalne: zapisuje historię raportów, a analizę można zrobić także bez logowania.",
    // 4.78s
    camera: [
      { t: 0, z: 1, x: 960, y: 540 },
      { t: 2, z: 1.05, x: 900, y: 510 },
      { t: 4.3, z: 1.03, x: 1020, y: 520 },
    ],
  },
  {
    id: 'logowanie',
    clip: '02-logowanie',
    from: 3.4,
    to: 20.6,
    rate: 1.3,
    title: "Logowanie",
    caption: "Zakładamy konto albo logujemy się od razu. Po zalogowaniu aplikacja wita rolnika po imieniu.",
    // 13.23s
    camera: [
      { t: 0, z: 1.05, x: 1250, y: 540 },
      { t: 3.6, z: 1.3, x: 1292, y: 490 },
      { t: 8.4, z: 1.3, x: 1292, y: 500 },
      { t: 10.8, z: 1.14, x: 1180, y: 460 },
      { t: 13.2, z: 1.03, x: 980, y: 420 },
    ],
  },
  {
    id: 'krok1',
    clip: '03-analiza',
    from: 2,
    to: 10.7,
    rate: 1.35,
    title: "Krok 1 · Twoje pole",
    caption: "Wystarczy numer działki z ewidencji — albo kliknięcie pola na mapie.",
    // 6.44s
    camera: [
      { t: 0, z: 1.02, x: 900, y: 430 },
      { t: 2, z: 1.1, x: 698, y: 640 },
      { t: 4.4, z: 1.14, x: 698, y: 700 },
      { t: 6.4, z: 1.05, x: 900, y: 600 },
    ],
  },
  {
    id: 'uprawa',
    clip: '03-analiza',
    from: 10.8,
    to: 17.2,
    rate: 1.3,
    title: "Krok 2 · Uprawa i data",
    caption: "Wybieramy uprawę i datę. Dla tej działki wynik jest już policzony: 15 czerwca 2026, pszenica ozima.",
    // 4.92s
    camera: [
      { t: 0, z: 1.05, x: 900, y: 420 },
      { t: 1.4, z: 1.2, x: 805, y: 365 },
      { t: 3.2, z: 1.2, x: 960, y: 690 },
      { t: 4.9, z: 1.08, x: 1050, y: 700 },
    ],
  },
  {
    id: 'ladowanie',
    clip: '03-analiza',
    from: 17.2,
    to: 27,
    rate: 2.2,
    title: "Analiza",
    caption: "Wodnik pobiera równolegle granice działki, model terenu, rowy, pogodę, glebę i zdjęcia satelitarne.",
    // 4.45s
    camera: [
      { t: 0, z: 1.05, x: 960, y: 430 },
      { t: 1.2, z: 1.22, x: 960, y: 500 },
      { t: 3, z: 1.22, x: 960, y: 560 },
      { t: 4.5, z: 1.1, x: 960, y: 500 },
    ],
  },
  {
    id: 'raport',
    clip: '03-analiza',
    from: 26.9,
    to: 31,
    title: "Twój raport",
    caption: "Pszenica jest już w stresie wodnym, ale w ostatnich latach bywało podobnie. Pewność analizy: średnia.",
    // 4.1s
    camera: [
      { t: 0, z: 1.02, x: 960, y: 340 },
      { t: 2.2, z: 1.06, x: 1010, y: 420 },
      { t: 4.4, z: 1.04, x: 1040, y: 470 },
    ],
  },
  {
    id: 'przyczyny',
    clip: '03-analiza',
    from: 31,
    to: 33.4,
    rate: 0.9,
    title: "Główna przyczyna",
    caption: "Lekka, piaszczysta gleba słabo trzyma wodę — a woda szybko odpływa z pola.",
    // 2.67s
    camera: [
      { t: 0, z: 1.04, x: 900, y: 460 },
      { t: 1.6, z: 1.24, x: 713, y: 520 },
      { t: 2.6, z: 1.23, x: 713, y: 530 },
    ],
  },
  {
    id: 'bilans',
    clip: '03-analiza',
    from: 33.4,
    to: 36.2,
    rate: 0.9,
    title: "Bilans wodny",
    caption: "Wykres pokazuje dziesięć lat tła: w 60% lat o tej porze było tu tak samo sucho lub suszej.",
    // 3.11s
    camera: [
      { t: 0, z: 1.08, x: 970, y: 500 },
      { t: 2, z: 1.34, x: 1160, y: 550 },
      { t: 3.1, z: 1.34, x: 1190, y: 570 },
    ],
  },
  {
    id: 'woda',
    clip: '04-wykresy',
    from: 10.2,
    to: 15.1,
    rate: 1.05,
    title: "Jak doszło do tej sytuacji?",
    caption: "Widać, kiedy zapas wody w glebie spadł poniżej progu stresu.",
    // 4.67s
    camera: [
      { t: 0, z: 1.05, x: 960, y: 150 },
      { t: 2, z: 1.16, x: 880, y: 150 },
      { t: 4.7, z: 1.1, x: 1100, y: 230 },
    ],
  },
  {
    id: 'opad',
    clip: '04-wykresy',
    from: 15.1,
    to: 19.4,
    rate: 1.05,
    title: "Opad i parowanie",
    caption: "Opad nie nadążał za parowaniem: w tym okresie 147 mm deszczu i 339 mm strat.",
    // 4.1s
    camera: [
      { t: 0, z: 1.08, x: 1000, y: 400 },
      { t: 2, z: 1.16, x: 850, y: 430 },
      { t: 4.1, z: 1.1, x: 1100, y: 470 },
    ],
  },
  {
    id: 'scenariusze',
    clip: '05-scenariusze',
    from: 10.2,
    to: 14.3,
    rate: 0.95,
    title: "Najbliższe 30 dni",
    caption: "Dziesięć scenariuszy pogody: 50% szans, że stres ustąpi, i 90% szans na silny stres.",
    // 4.32s
    camera: [
      { t: 0, z: 1.03, x: 960, y: 100 },
      { t: 1.6, z: 1.12, x: 900, y: 120 },
      { t: 4.3, z: 1.06, x: 1050, y: 180 },
    ],
  },
  {
    id: 'scen-wykres',
    clip: '05-scenariusze',
    from: 14.2,
    to: 19,
    rate: 0.95,
    title: "Pasmo scenariuszy",
    caption: "Pasmo pokazuje rozrzut od suchych do mokich lat, a linia przerywana — próg stresu.",
    // 5.05s
    camera: [
      { t: 0, z: 1.06, x: 1000, y: 250 },
      { t: 2.2, z: 1.14, x: 880, y: 330 },
      { t: 5.1, z: 1.06, x: 1120, y: 400 },
    ],
  },
  {
    id: 'retencja',
    clip: '06-retencja',
    from: 10.6,
    to: 14.8,
    title: "Co da retencja",
    caption: "Przy ulewie 50 mm z tej działki i sąsiednich pól spłynie ponad tysiąc metrów sześciennych wody.",
    // 4.2s
    camera: [
      { t: 0, z: 1.03, x: 960, y: 180 },
      { t: 2, z: 1.1, x: 960, y: 220 },
      { t: 4.1, z: 1.06, x: 1000, y: 260 },
    ],
  },
  {
    id: 'ulewy',
    clip: '06-retencja',
    from: 14.8,
    to: 18.5,
    title: "Ulewy",
    caption: "Dla ulewy 30 mm to 193 m³ spływu, dla 50 mm — 1026 m³.",
    // 3.7s
    camera: [
      { t: 0, z: 1.1, x: 880, y: 180 },
      { t: 2, z: 1.22, x: 760, y: 180 },
      { t: 3.6, z: 1.18, x: 1120, y: 185 },
    ],
  },
  {
    id: 'srodki',
    clip: '06-retencja',
    from: 18.4,
    to: 24.2,
    title: "Trzy działania",
    caption: "Około 430 metrów niskiego wału, 781 m³ wody w oczku i 5 mm więcej wody w glebie przy każdym deszczu.",
    // 5.8s
    camera: [
      { t: 0, z: 1.08, x: 800, y: 300 },
      { t: 1.6, z: 1.3, x: 620, y: 310 },
      { t: 3.4, z: 1.4, x: 963, y: 330 },
      { t: 5.8, z: 1.3, x: 1290, y: 360 },
    ],
  },
  {
    id: 'tabela',
    clip: '07-zalecenia',
    from: 10.6,
    to: 16.8,
    rate: 1.3,
    title: "Zalecenia",
    caption: "Każda rada ma miejsce na działce, uzasadnienie i poziom pewności.",
    // 4.77s
    camera: [
      { t: 0, z: 1.05, x: 960, y: 250 },
      { t: 2, z: 1.14, x: 800, y: 300 },
      { t: 4.8, z: 1.1, x: 1000, y: 380 },
    ],
  },
  {
    id: 'agro',
    clip: '07-zalecenia',
    from: 16.8,
    to: 22.4,
    rate: 1.35,
    title: "Agrotechnika",
    caption: "Międzyplony, resztki pożniwne i uprawa ograniczająca parowanie — najmocniejsza retencja na lekkich glebach.",
    // 4.15s
    camera: [
      { t: 0, z: 1.06, x: 900, y: 280 },
      { t: 2, z: 1.14, x: 700, y: 320 },
      { t: 4.1, z: 1.1, x: 1000, y: 380 },
    ],
  },
  {
    id: 'czat-pytanie1',
    clip: '08-asystent',
    from: 10.6,
    to: 17.6,
    rate: 1.4,
    title: "Asystent",
    caption: "Rolnik może po prostu zapytać. Asystent zna cały raport.",
    // 5s
    camera: [
      { t: 0, z: 1.08, x: 1000, y: 620 },
      { t: 2, z: 1.3, x: 963, y: 650 },
      { t: 4.9, z: 1.24, x: 900, y: 600 },
    ],
  },
  {
    id: 'czat-odpowiedz1',
    clip: '08-asystent',
    from: 17.5,
    to: 30.1,
    rate: 1.7,
    title: "Odpowiedź",
    caption: "Odpowiada prostym językiem i trzyma się liczb z raportu.",
    // 7.41s
    camera: [
      { t: 0, z: 1.1, x: 960, y: 600 },
      { t: 2.6, z: 1.34, x: 1000, y: 660 },
      { t: 7.4, z: 1.3, x: 1000, y: 700 },
    ],
  },
  {
    id: 'czat-pytanie2',
    clip: '08-asystent',
    from: 28.6,
    to: 34.7,
    rate: 1.5,
    title: "Pytanie o przepisy",
    caption: "Pyta też o formalności: „Czy muszę mieć zgodę na wał?”",
    // 4.07s
    camera: [
      { t: 0, z: 1.15, x: 900, y: 640 },
      { t: 2, z: 1.3, x: 913, y: 700 },
      { t: 4.1, z: 1.25, x: 950, y: 680 },
    ],
  },
  {
    id: 'czat-odpowiedz2',
    clip: '08-asystent',
    from: 34.7,
    to: 39.8,
    title: "Asystent doradza",
    caption: "Przy rowach, stawach i poborze wody odsyła do doradcy ODR i Prawa wodnego.",
    // 5.1s
    camera: [
      { t: 0, z: 1.1, x: 960, y: 660 },
      { t: 1.6, z: 1.24, x: 960, y: 540 },
      { t: 5.1, z: 1.2, x: 960, y: 520 },
    ],
  },
  {
    id: 'druk',
    clip: '09-druk',
    from: 11,
    to: 15.2,
    rate: 1.1,
    title: "Wydruk",
    caption: "Raport można wydrukować dla doradcy albo załączyć do wniosku.",
    // 3.82s
    camera: [
      { t: 0, z: 1.06, x: 960, y: 800 },
      { t: 1.6, z: 1.3, x: 1250, y: 840 },
      { t: 3.8, z: 1.26, x: 1300, y: 862 },
    ],
  },
  {
    id: 'wydruk-gora',
    clip: '10-wydruk',
    from: 2.3,
    to: 7.5,
    rate: 0.95,
    title: "Raport do druku",
    caption: "Jedna strona: ocena, przyczyny, liczby i mapa punktów.",
    // 5.47s
    camera: [
      { t: 0, z: 1.5, x: 960, y: 500 },
      { t: 1.8, z: 1.7, x: 960, y: 460 },
      { t: 3.6, z: 1.66, x: 960, y: 600 },
    ],
  },
  {
    id: 'wydruk-wykresy',
    clip: '10-wydruk',
    from: 7.4,
    to: 10.8,
    rate: 0.95,
    title: "Wykresy w raporcie",
    caption: "Wszystkie wykresy trafiają też na wydruk.",
    // 3.58s
    camera: [
      { t: 0, z: 1.7, x: 960, y: 420 },
      { t: 1.8, z: 1.85, x: 960, y: 380 },
      { t: 3.6, z: 1.8, x: 1000, y: 500 },
    ],
  },
  {
    id: 'wydruk-lata',
    clip: '10-wydruk',
    from: 10.7,
    to: 13.2,
    rate: 0.95,
    title: "Tło wieloletnie",
    caption: "Ten rok na tle poprzednich lat — z progiem wyraźnego deficytu.",
    // 2.63s
    camera: [
      { t: 0, z: 1.8, x: 960, y: 380 },
      { t: 2.5, z: 1.86, x: 960, y: 400 },
    ],
  },
  {
    id: 'profil',
    clip: '11-profil',
    from: 15,
    to: 19.1,
    rate: 1.1,
    title: "Twoje konto",
    caption: "Konto zapisuje historię raportów.",
    // 3.73s
    camera: [
      { t: 0, z: 1.03, x: 900, y: 260 },
      { t: 1.8, z: 1.07, x: 820, y: 280 },
      { t: 3.7, z: 1.04, x: 1000, y: 340 },
    ],
  },
  {
    id: 'historia',
    clip: '11-profil',
    from: 19.2,
    to: 25.1,
    rate: 1.2,
    title: "Historia raportów",
    caption: "Każdą analizę można otworzyć, wydrukować albo usunąć.",
    // 4.92s
    camera: [
      { t: 0, z: 1.06, x: 1100, y: 420 },
      { t: 2, z: 1.24, x: 1300, y: 420 },
      { t: 4.9, z: 1.16, x: 1000, y: 420 },
    ],
  },
  {
    id: 'powrot',
    clip: '12-powrot',
    from: 10.5,
    to: 15.3,
    rate: 0.95,
    title: "Wodnik",
    caption: "Zatrzymaj wodę, chroń plony.",
    // 5.05s
    camera: [
      { t: 0, z: 1.03, x: 960, y: 520 },
      { t: 2.4, z: 1.05, x: 820, y: 500 },
      { t: 5.1, z: 1.02, x: 900, y: 520 },
    ],
  },
  {
    id: 'outro',
    kind: 'outro',
    from: 0,
    to: 5,
    // 5s
  },
]

export const sceneDuration = (scene: Scene, fps: number) =>
  Math.round(((scene.to - scene.from) / (scene.rate ?? 1)) * fps)
