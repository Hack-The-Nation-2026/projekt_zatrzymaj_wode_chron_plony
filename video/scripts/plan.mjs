import { readFile, writeFile } from 'node:fs/promises'

/**
 * Montaż opisany raz, w jednym miejscu. Każda scena mówi, z którego nagrania
 * bierze obraz i gdzie się zaczyna:
 *
 *   { mark: 'raport', seconds: 5, rate: 1.2 } od znacznika, zadana długość na ekranie
 *   { mark: 'raport', until: 'przyczyny', tail: 0.5 } od znacznika do znacznika
 *   { from: 12.4, to: 20.1, rate: 1.1 } konkretny wycinek nagrania
 *
 * `lead` przesuwa początek względem znacznika (może być ujemny), `tail` cofa
 * koniec przed następnym znacznikiem. `seconds` to czas na ekranie, więc wycinek
 * źródłowy to `seconds * rate`.
 *
 * Każda scena niesie polski napis: `title` to mała etykieta nad zdaniem, a
 * `caption` to zdanie lektora, bo część jury ogląda film bez dźwięku.
 *
 * Kamera: `t` w sekundach od początku sceny, `z` to powiększenie, `x`/`y` to punkt
 * kadru w nagraniu 1920×1080. Zbliżamy tylko tam, gdzie jest na co patrzeć.
 */

// prettier-ignore
const PLAN = [
  // ── Strona startowa: problem, pitch, ścieżka KOWR, dane, model ────────
  { id: 'hero', clip: '01-start', mark: 'start', lead: -1.8, until: 'liczby', tail: 0.6, rate: 0.85,
    title: 'Wodnik', caption: 'Susza to już nie wyjątek, tylko codzienność polskiego rolnictwa. Za każdą płacimy po fakcie — miliardami złotych pomocy.',
    camera: [{ t: 0, z: 1, x: 960, y: 540 }, { t: 3, z: 1.05, x: 860, y: 500 }, { t: 7, z: 1.03, x: 900, y: 520 }] },
  { id: 'liczby', clip: '01-start', mark: 'liczby', lead: -0.4, until: 'pitch', tail: 0.6, rate: 0.95,
    title: 'Problem', caption: 'Polska zatrzymuje tylko 7,5 procent wody, która przez nią przepływa. Za susze 2018–2019 zapłaciliśmy 4,36 mld zł.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 420 }, { t: 2, z: 1.08, x: 880, y: 430 }, { t: 4.6, z: 1.04, x: 950, y: 440 }] },
  { id: 'pitch', clip: '01-start', mark: 'pitch', lead: -0.4, until: 'kroki', tail: 0.5, rate: 0.95,
    title: 'Dlaczego Wodnik', caption: 'Rolnik zna swoje pole. Łączenie zdjęć satelitarnych, modeli terenu i pogody z dziesięciu lat bierzemy na siebie.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 460 }, { t: 1.6, z: 1.08, x: 1000, y: 460 }, { t: 3.6, z: 1.04, x: 1060, y: 470 }] },
  { id: 'kroki', clip: '01-start', mark: 'kroki', lead: -0.4, until: 'zrodla', tail: 0.5, rate: 0.95,
    title: 'Kolejność KOWR', caption: 'Ocena, przyczyny, retencja, agrotechnika — a nawadnianie na końcu. Dokładnie w tej kolejności.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 390 }, { t: 2, z: 1.07, x: 960, y: 400 }, { t: 4.4, z: 1.03, x: 960, y: 420 }] },
  { id: 'zrodla', clip: '01-start', mark: 'zrodla', lead: -0.4, until: 'model', tail: 0.5, rate: 0.95,
    title: 'Pięć źródeł danych', caption: 'GUGiK, BDOT10k, Copernicus ERA5, Sentinel-2 i SoilGrids. Dane publiczne, liczone od nowa dla każdej działki.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 390 }, { t: 2, z: 1.07, x: 960, y: 420 }, { t: 4.4, z: 1.03, x: 960, y: 440 }] },
  { id: 'model', clip: '01-start', mark: 'model', lead: -0.5, until: 'powrot', tail: 0.6, rate: 0.95,
    title: 'Model biznesowy', caption: 'Dla rolnika za darmo. Kanałem są KOWR i ośrodki doradztwa, a wartość dla państwa to mniej strat po suszy.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 400 }, { t: 2.4, z: 1.06, x: 960, y: 480 }, { t: 4.8, z: 1.06, x: 960, y: 560 }, { t: 6.4, z: 1.03, x: 960, y: 600 }] },
  { id: 'konto', clip: '01-start', mark: 'powrot', lead: -0.6, until: '__koniec', tail: 0.3, rate: 0.9,
    title: 'Konto', caption: 'Konto jest opcjonalne: zapisuje historię raportów, a analizę można zrobić także bez logowania.',
    camera: [{ t: 0, z: 1, x: 960, y: 540 }, { t: 2, z: 1.05, x: 900, y: 510 }, { t: 4.3, z: 1.03, x: 1020, y: 520 }] },

  // ── Logowanie i witamy w aplikacji ────────────────────────────────────
  { id: 'logowanie', clip: '02-logowanie', mark: 'karta', lead: -0.6, until: '__koniec', tail: 0.3, rate: 1.3,
    title: 'Logowanie', caption: 'Zakładamy konto albo logujemy się od razu. Po zalogowaniu aplikacja wita rolnika po imieniu.',
    camera: [{ t: 0, z: 1.05, x: 1250, y: 540 }, { t: 3.6, z: 1.3, x: 1292, y: 490 }, { t: 8.4, z: 1.3, x: 1292, y: 500 }, { t: 10.8, z: 1.14, x: 1180, y: 460 }, { t: 13.2, z: 1.03, x: 980, y: 420 }] },

  // ── Krok 1 i 2, potem prawdziwy ekran postępu ─────────────────────────
  { id: 'krok1', clip: '03-analiza', mark: 'pole', lead: -0.6, until: 'uprawa', tail: 0.4, rate: 1.35,
    title: 'Krok 1 · Twoje pole', caption: 'Wystarczy numer działki z ewidencji — albo kliknięcie pola na mapie.',
    camera: [{ t: 0, z: 1.02, x: 900, y: 430 }, { t: 2, z: 1.1, x: 698, y: 640 }, { t: 4.4, z: 1.14, x: 698, y: 700 }, { t: 6.4, z: 1.05, x: 900, y: 600 }] },
  { id: 'uprawa', clip: '03-analiza', mark: 'uprawa', lead: -0.3, until: 'ladowanie', tail: 0.4, rate: 1.3,
    title: 'Krok 2 · Uprawa i data', caption: 'Wybieramy uprawę i datę. Dla tej działki wynik jest już policzony: 15 czerwca 2026, pszenica ozima.',
    camera: [{ t: 0, z: 1.05, x: 900, y: 420 }, { t: 1.4, z: 1.2, x: 805, y: 365 }, { t: 3.2, z: 1.2, x: 960, y: 690 }, { t: 4.9, z: 1.08, x: 1050, y: 700 }] },
  { id: 'ladowanie', clip: '03-analiza', mark: 'ladowanie', lead: -0.4, until: 'raport', tail: 0.5, rate: 2.2,
    title: 'Analiza', caption: 'Wodnik pobiera równolegle granice działki, model terenu, rowy, pogodę, glebę i zdjęcia satelitarne.',
    camera: [{ t: 0, z: 1.05, x: 960, y: 430 }, { t: 1.2, z: 1.22, x: 960, y: 500 }, { t: 3, z: 1.22, x: 960, y: 560 }, { t: 4.5, z: 1.1, x: 960, y: 500 }] },

  // ── Wynik: ryzyko, w skrócie, przyczyny, bilans wodny ─────────────────
  { id: 'raport', clip: '03-analiza', mark: 'raport', lead: -0.6, until: 'przyczyny', tail: 0.3, rate: 1,
    title: 'Twój raport', caption: 'Pszenica jest już w stresie wodnym, ale w ostatnich latach bywało podobnie. Pewność analizy: średnia.',
    camera: [{ t: 0, z: 1.02, x: 960, y: 340 }, { t: 2.2, z: 1.06, x: 1010, y: 420 }, { t: 4.4, z: 1.04, x: 1040, y: 470 }] },
  { id: 'przyczyny', clip: '03-analiza', mark: 'przyczyny', lead: -0.3, until: 'bilans', tail: 0.3, rate: 0.9,
    title: 'Główna przyczyna', caption: 'Lekka, piaszczysta gleba słabo trzyma wodę — a woda szybko odpływa z pola.',
    camera: [{ t: 0, z: 1.04, x: 900, y: 460 }, { t: 1.6, z: 1.24, x: 713, y: 520 }, { t: 2.6, z: 1.23, x: 713, y: 530 }] },
  { id: 'bilans', clip: '03-analiza', mark: 'bilans', lead: -0.3, until: '__koniec', tail: 0.3, rate: 0.9,
    title: 'Bilans wodny', caption: 'Wykres pokazuje dziesięć lat tła: w 60% lat o tej porze było tu tak samo sucho lub suszej.',
    camera: [{ t: 0, z: 1.08, x: 970, y: 500 }, { t: 2, z: 1.34, x: 1160, y: 550 }, { t: 3.1, z: 1.34, x: 1190, y: 570 }] },

  // ── Wykresy: woda w glebie oraz opad i parowanie ──────────────────────
  { id: 'woda', clip: '04-wykresy', mark: 'historia', lead: -0.6, until: 'opad', tail: 0.4, rate: 1.05,
    title: 'Jak doszło do tej sytuacji?', caption: 'Widać, kiedy zapas wody w glebie spadł poniżej progu stresu.',
    camera: [{ t: 0, z: 1.05, x: 960, y: 150 }, { t: 2, z: 1.16, x: 880, y: 150 }, { t: 4.7, z: 1.1, x: 1100, y: 230 }] },
  { id: 'opad', clip: '04-wykresy', mark: 'opad', lead: -0.4, until: '__koniec', tail: 0.4, rate: 1.05,
    title: 'Opad i parowanie', caption: 'Opad nie nadążał za parowaniem: w tym okresie 147 mm deszczu i 339 mm strat.',
    camera: [{ t: 0, z: 1.08, x: 1000, y: 400 }, { t: 2, z: 1.16, x: 850, y: 430 }, { t: 4.1, z: 1.1, x: 1100, y: 470 }] },

  // ── Scenariusze na najbliższe 30 dni ──────────────────────────────────
  { id: 'scenariusze', clip: '05-scenariusze', mark: 'scenariusze', lead: -0.6, until: 'scen-wykres', tail: 0.3, rate: 0.95,
    title: 'Najbliższe 30 dni', caption: 'Dziesięć scenariuszy pogody: 50% szans, że stres ustąpi, i 90% szans na silny stres.',
    camera: [{ t: 0, z: 1.03, x: 960, y: 100 }, { t: 1.6, z: 1.12, x: 900, y: 120 }, { t: 4.3, z: 1.06, x: 1050, y: 180 }] },
  { id: 'scen-wykres', clip: '05-scenariusze', mark: 'scen-wykres', lead: -0.4, until: '__koniec', tail: 0.4, rate: 0.95,
    title: 'Pasmo scenariuszy', caption: 'Pasmo pokazuje rozrzut od suchych do mokich lat, a linia przerywana — próg stresu.',
    camera: [{ t: 0, z: 1.06, x: 1000, y: 250 }, { t: 2.2, z: 1.14, x: 880, y: 330 }, { t: 5.1, z: 1.06, x: 1120, y: 400 }] },

  // ── „Co da retencja na tej działce” i liczby ──────────────────────────
  { id: 'retencja', clip: '06-retencja', mark: 'retencja', lead: -0.8, until: 'ulewy', tail: 0.3, rate: 1,
    title: 'Co da retencja', caption: 'Przy ulewie 50 mm z tej działki i sąsiednich pól spłynie ponad tysiąc metrów sześciennych wody.',
    camera: [{ t: 0, z: 1.03, x: 960, y: 180 }, { t: 2, z: 1.1, x: 960, y: 220 }, { t: 4.1, z: 1.06, x: 1000, y: 260 }] },
  { id: 'ulewy', clip: '06-retencja', mark: 'ulewy', lead: -0.3, until: 'srodki', tail: 0.3, rate: 1,
    title: 'Ulewy', caption: 'Dla ulewy 30 mm to 193 m³ spływu, dla 50 mm — 1026 m³.',
    camera: [{ t: 0, z: 1.1, x: 880, y: 180 }, { t: 2, z: 1.22, x: 760, y: 180 }, { t: 3.6, z: 1.18, x: 1120, y: 185 }] },
  { id: 'srodki', clip: '06-retencja', mark: 'srodki', lead: -0.4, until: '__koniec', tail: 0.5, rate: 1,
    title: 'Trzy działania', caption: 'Około 430 metrów niskiego wału, 781 m³ wody w oczku i 5 mm więcej wody w glebie przy każdym deszczu.',
    camera: [{ t: 0, z: 1.08, x: 800, y: 300 }, { t: 1.6, z: 1.3, x: 620, y: 310 }, { t: 3.4, z: 1.4, x: 963, y: 330 }, { t: 5.8, z: 1.3, x: 1290, y: 360 }] },

  // ── Tabela zaleceń: ścieżka KOWR ──────────────────────────────────────
  { id: 'tabela', clip: '07-zalecenia', mark: 'tabela', lead: -0.6, until: 'agro', tail: 0.4, rate: 1.3,
    title: 'Zalecenia', caption: 'Każda rada ma miejsce na działce, uzasadnienie i poziom pewności.',
    camera: [{ t: 0, z: 1.05, x: 960, y: 250 }, { t: 2, z: 1.14, x: 800, y: 300 }, { t: 4.8, z: 1.1, x: 1000, y: 380 }] },
  { id: 'agro', clip: '07-zalecenia', mark: 'agro', lead: -0.4, until: 'nawadnianie', tail: 0.4, rate: 1.35,
    title: 'Agrotechnika', caption: 'Międzyplony, resztki pożniwne i uprawa ograniczająca parowanie — najmocniejsza retencja na lekkich glebach.',
    camera: [{ t: 0, z: 1.06, x: 900, y: 280 }, { t: 2, z: 1.14, x: 700, y: 320 }, { t: 4.1, z: 1.1, x: 1000, y: 380 }] },

  // ── Asystent: podpowiedź z listy i własne pytanie o przepisy ──────────
  { id: 'czat-pytanie1', clip: '08-asystent', mark: 'czat', lead: -0.6, until: 'pisze1', tail: 0.4, rate: 1.4,
    title: 'Asystent', caption: 'Rolnik może po prostu zapytać. Asystent zna cały raport.',
    camera: [{ t: 0, z: 1.08, x: 1000, y: 620 }, { t: 2, z: 1.3, x: 963, y: 650 }, { t: 4.9, z: 1.24, x: 900, y: 600 }] },
  { id: 'czat-odpowiedz1', clip: '08-asystent', mark: 'pisze1', lead: -0.5, until: 'pytanie2', tail: 1,
    rate: 1.7,
    title: 'Odpowiedź', caption: 'Odpowiada prostym językiem i trzyma się liczb z raportu.',
    camera: [{ t: 0, z: 1.1, x: 960, y: 600 }, { t: 2.6, z: 1.34, x: 1000, y: 660 }, { t: 7.4, z: 1.3, x: 1000, y: 700 }] },
  { id: 'czat-pytanie2', clip: '08-asystent', mark: 'pytanie2', lead: -2.5, until: 'odpowiedz2', tail: 0.6, rate: 1.5,
    title: 'Pytanie o przepisy', caption: 'Pyta też o formalności: „Czy muszę mieć zgodę na wał?”',
    camera: [{ t: 0, z: 1.15, x: 900, y: 640 }, { t: 2, z: 1.3, x: 913, y: 700 }, { t: 4.1, z: 1.25, x: 950, y: 680 }] },
  { id: 'czat-odpowiedz2', clip: '08-asystent', mark: 'odpowiedz2', lead: -0.6, until: '__koniec', tail: 0.5, rate: 1,
    title: 'Asystent doradza', caption: 'Przy rowach, stawach i poborze wody odsyła do doradcy ODR i Prawa wodnego.',
    camera: [{ t: 0, z: 1.1, x: 960, y: 660 }, { t: 1.6, z: 1.24, x: 960, y: 540 }, { t: 5.1, z: 1.2, x: 960, y: 520 }] },

  // ── Druk, raport do wydruku i historia w profilu ──────────────────────
  { id: 'druk', clip: '09-druk', mark: 'stopka', lead: -0.5, until: 'druk', tail: -0.2, rate: 1.1,
    title: 'Wydruk', caption: 'Raport można wydrukować dla doradcy albo załączyć do wniosku.',
    camera: [{ t: 0, z: 1.06, x: 960, y: 800 }, { t: 1.6, z: 1.3, x: 1250, y: 840 }, { t: 3.8, z: 1.26, x: 1300, y: 862 }] },
  { id: 'wydruk-gora', clip: '10-wydruk', mark: 'druk-gora', lead: -0.5, until: 'druk-wykresy', tail: 0.3, rate: 0.95,
    title: 'Raport do druku', caption: 'Jedna strona: ocena, przyczyny, liczby i mapa punktów.',
    camera: [{ t: 0, z: 1.5, x: 960, y: 500 }, { t: 1.8, z: 1.7, x: 960, y: 460 }, { t: 3.6, z: 1.66, x: 960, y: 600 }] },
  { id: 'wydruk-wykresy', clip: '10-wydruk', mark: 'druk-wykresy', lead: -0.4, until: 'druk-lata', tail: 0.3, rate: 0.95,
    title: 'Wykresy w raporcie', caption: 'Wszystkie wykresy trafiają też na wydruk.',
    camera: [{ t: 0, z: 1.7, x: 960, y: 420 }, { t: 1.8, z: 1.85, x: 960, y: 380 }, { t: 3.6, z: 1.8, x: 1000, y: 500 }] },
  { id: 'wydruk-lata', clip: '10-wydruk', mark: 'druk-lata', lead: -0.4, until: '__koniec', tail: 0.3, rate: 0.95,
    title: 'Tło wieloletnie', caption: 'Ten rok na tle poprzednich lat — z progiem wyraźnego deficytu.',
    camera: [{ t: 0, z: 1.8, x: 960, y: 380 }, { t: 2.5, z: 1.86, x: 960, y: 400 }] },
  { id: 'profil', clip: '11-profil', mark: 'profil', lead: -0.6, until: 'historia', tail: 0.4, rate: 1.1,
    title: 'Twoje konto', caption: 'Konto zapisuje historię raportów.',
    camera: [{ t: 0, z: 1.03, x: 900, y: 260 }, { t: 1.8, z: 1.07, x: 820, y: 280 }, { t: 3.7, z: 1.04, x: 1000, y: 340 }] },
  { id: 'historia', clip: '11-profil', mark: 'historia', lead: -0.3, until: '__koniec', tail: 0.4, rate: 1.2,
    title: 'Historia raportów', caption: 'Każdą analizę można otworzyć, wydrukować albo usunąć.',
    camera: [{ t: 0, z: 1.06, x: 1100, y: 420 }, { t: 2, z: 1.24, x: 1300, y: 420 }, { t: 4.9, z: 1.16, x: 1000, y: 420 }] },

  // ── Powrót na stronę startową ─────────────────────────────────────────
  { id: 'powrot', clip: '12-powrot', mark: 'logo', lead: -0.7, until: '__koniec', tail: 0.3, rate: 0.95,
    title: 'Wodnik', caption: 'Zatrzymaj wodę, chroń plony.',
    camera: [{ t: 0, z: 1.03, x: 960, y: 520 }, { t: 2.4, z: 1.05, x: 820, y: 500 }, { t: 5.1, z: 1.02, x: 900, y: 520 }] },
]

const TAKES = [
  '01-start', '02-logowanie', '03-analiza', '04-wykresy', '05-scenariusze', '06-retencja',
  '07-zalecenia', '08-asystent', '09-druk', '10-wydruk', '11-profil', '12-powrot',
]

const marks = {}
for (const name of TAKES) {
  try {
    marks[name] = JSON.parse(await readFile(`out/marks-${name}.json`, 'utf8'))
  } catch {
    /* brak nagrania, więc scena wypadnie z montażu */
  }
}

const round = (value) => Number(value.toFixed(2))
const problems = []
const scenes = []

for (const scene of PLAN) {
  const table = marks[scene.clip]
  if (!table) {
    problems.push(`${scene.id}: brak nagrania ${scene.clip}`)
    continue
  }
  const end = table.__koniec
  let from
  let to
  if (scene.from != null && scene.to != null) {
    from = scene.from
    to = scene.to
  } else {
    if (table[scene.mark] == null) {
      problems.push(`${scene.id}: brak znacznika ${scene.mark} w ${scene.clip}`)
      continue
    }
    from = table[scene.mark] + (scene.lead ?? 0)
    if (scene.until != null) {
      if (table[scene.until] == null) {
        problems.push(`${scene.id}: brak znacznika ${scene.until} w ${scene.clip}`)
        continue
      }
      to = table[scene.until] - (scene.tail ?? 0.5)
    } else {
      to = from + scene.seconds * (scene.rate ?? 1)
    }
  }
  from = Math.max(0, round(from))
  to = round(to)
  if (to <= from) {
    problems.push(`${scene.id}: wycinek pusty (${from} → ${to})`)
    continue
  }
  if (end != null && to > end + 0.05) problems.push(`${scene.id}: wycinek do ${to}s, a nagranie ma ${end}s`)
  scenes.push({ ...scene, from, to, seconds: round((to - from) / (scene.rate ?? 1)) })
}

// Karta końcowa z adresem demo i kodem QR. Nie pochodzi z nagrania, więc ma własny
// wymiar: pięć sekund na odczytanie kodu.
const OUTRO_SECONDS = 5
scenes.push({ id: 'outro', kind: 'outro', from: 0, to: OUTRO_SECONDS, seconds: OUTRO_SECONDS })

const render = (scene) => {
  const camera = scene.camera ?? [{ t: 0, z: 1, x: 960, y: 540 }]
  const framed = scene.kind === 'outro'
  return [
    '  {',
    `    id: '${scene.id}',`,
    scene.kind === 'outro' ? "    kind: 'outro'," : null,
    scene.clip ? `    clip: '${scene.clip}',` : null,
    `    from: ${scene.from},`,
    `    to: ${scene.to},`,
    scene.rate && scene.rate !== 1 ? `    rate: ${scene.rate},` : null,
    scene.title ? `    title: ${JSON.stringify(scene.title)},` : null,
    scene.caption ? `    caption: ${JSON.stringify(scene.caption)},` : null,
    `    // ${scene.seconds}s`,
    framed
      ? null
      : `    camera: [\n${camera.map((key) => `      { t: ${key.t}, z: ${key.z}, x: ${key.x}, y: ${key.y} },`).join('\n')}\n    ],`,
    '  },',
  ]
    .filter(Boolean)
    .join('\n')
}

const header = `export type CameraKey = {
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
`

const footer = `]

export const sceneDuration = (scene: Scene, fps: number) =>
  Math.round(((scene.to - scene.from) / (scene.rate ?? 1)) * fps)
`

await writeFile('src/edl.ts', header + scenes.map(render).join('\n') + '\n' + footer)

const byClip = {}
for (const scene of scenes) {
  if (!scene.clip) continue
  byClip[scene.clip] = (byClip[scene.clip] ?? 0) + scene.seconds
}
const total = scenes.reduce((sum, scene) => sum + scene.seconds, 0)
console.log(`${scenes.length} scen, ${total.toFixed(1)}s`)
for (const [clip, seconds] of Object.entries(byClip)) console.log(`  ${clip.padEnd(22)} ${seconds.toFixed(1)}s`)
for (const problem of problems) console.log(`  ! ${problem}`)
