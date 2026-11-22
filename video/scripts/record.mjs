import {
  launch, openScene, finishScene, moveTo, clickAt, ensureVisible, settle, typeInto,
  scrollPage, scrollBy, reveal, scrollToTop, saveStorage, ensureLoginState,
} from './lib.mjs'
import { DEMO, loadDemo, stageLoading, pickParcelOnCamera, confirmCropOnCamera } from './app.mjs'
import { writeFile } from 'node:fs/promises'

const TAKE = process.argv[2] ?? 'all'
const STATE = 'public/clips/state-login.json'
const PRINT_URL = '/api/v1/analyses/demo-lazisko_352_2026_06_15/raport'

/** Znaczniki czasu: montaż bierze z nich początki scen, zamiast zgadywać sekundy. */
const marks = {}
let takeStart = 0
function mark(label) {
  marks[label] = Number(((Date.now() - takeStart) / 1000).toFixed(1))
  console.log(`  ⏱ ${label} @ ${marks[label]}s`)
}

async function take(name, browser, options, run) {
  const started = Date.now()
  takeStart = started
  const scene = await openScene(browser, name, options)
  console.log(`▶ ${name}`)
  try {
    await run(scene.page, scene)
    const seconds = (Date.now() - started) / 1000
    console.log(`  ${name}: ${seconds.toFixed(1)}s`)
    marks['__koniec'] = Number(seconds.toFixed(1))
    await writeFile(`out/marks-${name}.json`, JSON.stringify(marks, null, 1))
    for (const key of Object.keys(marks)) delete marks[key]
  } catch (error) {
    console.error(`✖ ${name}: ${error.message}`)
    const summary = await scene.page.evaluate(() => ({
      url: location.pathname,
      buttons: [...document.querySelectorAll('button')].map((b) => b.getAttribute('aria-label') || (b.textContent || '').trim().slice(0, 28)).slice(0, 16),
      headings: [...document.querySelectorAll('h1,h2')].map((h) => h.textContent.trim().slice(0, 40)).slice(0, 10),
    })).catch(() => null)
    if (summary) console.error('  stan:', JSON.stringify(summary))
    await scene.page.screenshot({ path: `public/clips/error-${name}.png` }).catch(() => {})
    await finishScene(scene)
    throw error
  }
  await finishScene(scene)
}

const browser = await launch()
const loggedIn = await ensureLoginState(browser, STATE)
console.log(loggedIn ? `konto ${DEMO.id ? '' : ''}gotowe (${STATE})` : '! nie udało się zalogować konta demo')
const AUTH = { storage: STATE }

/* --------------------------------------------------------- 01: strona startowa */

if (TAKE === 'all' || TAKE === '01-start') {
  await take('01-start', browser, { url: '/' }, async (page) => {
    await settle(page, 1600)
    mark('start')
    // Najpierw hasło i zdjęcie, potem karta logowania po prawej.
    await moveTo(page, 716, 500, { pause: 900 })
    await moveTo(page, 1292, 565, { pause: 700 })
    await settle(page, 500)

    // „Za suszę płacimy po fakcie” – liczby o problemie.
    await reveal(page, page.getByRole('heading', { name: /Za suszę płacimy po fakcie/i }).first(), { at: 0.32 })
    mark('liczby')
    await moveTo(page, 784, 346, { pause: 520 })
    await moveTo(page, 960, 486, { pause: 900 })
    await settle(page, 500)

    // „Rolnik zna swoje pole. My dokładamy dane.” – pitch i podgląd raportu.
    await reveal(page, page.getByRole('heading', { name: /Rolnik zna swoje pole/i }).first(), { at: 0.34 })
    mark('pitch')
    await settle(page, 600)
    await moveTo(page, 1275, 470, { pause: 1000 })
    await settle(page, 600)

    // Pięć kroków ścieżki KOWR.
    await reveal(page, page.getByRole('heading', { name: /Od diagnozy do działania/i }).first(), { at: 0.3 })
    mark('kroki')
    await moveTo(page, 620, 380, { pause: 500 })
    await moveTo(page, 960, 456, { pause: 900 })
    await settle(page, 500)

    // Pięć źródeł danych.
    await reveal(page, page.getByRole('heading', { name: /Pięć źródeł danych/i }).first(), { at: 0.3 })
    mark('zrodla')
    await moveTo(page, 700, 400, { pause: 500 })
    await moveTo(page, 1150, 500, { pause: 900 })
    await settle(page, 500)

    // Model biznesowy i plan wdrożenia.
    await reveal(page, page.getByRole('heading', { name: /Darmowe dla rolnika/i }).first(), { at: 0.3 })
    mark('model')
    await moveTo(page, 780, 420, { pause: 500 })
    await moveTo(page, 960, 600, { pause: 700 })
    await moveTo(page, 960, 752, { pause: 900 })
    await settle(page, 600)

    // Powrót na górę: hasło i karta logowania znów w kadrze.
    await scrollToTop(page, { settleMs: 1500 })
    mark('powrot')
    await moveTo(page, 716, 500, { pause: 800 })
    await moveTo(page, 1292, 540, { pause: 900 })
    await settle(page, 600)
  })
}

/* ------------------------------------------------------------- 02: logowanie */

if (TAKE === 'all' || TAKE === '02-logowanie') {
  await take('02-logowanie', browser, { url: '/' }, async (page, scene) => {
    await settle(page, 1400)
    await moveTo(page, 1112, 432, { pause: 700 })
    mark('karta')
    await settle(page, 500)
    await typeInto(page, page.locator('#lp-email'), 'film@wodnik.test', { perChar: [70, 150] })
    await typeInto(page, page.locator('#lp-pass'), 'wodnik-film-2026', { perChar: [60, 130] })
    await clickAt(page, page.getByRole('button', { name: 'Zaloguj się', exact: true }).first(), { x: 0, y: 0 }, 2400)

    // Aplikacja: powitanie po imieniu i pasek kroków.
    await page.getByRole('heading', { name: /Gdzie jest Twoje pole/i }).first().waitFor({ timeout: 25000 })
    await scrollToTop(page, { settleMs: 900 })
    await settle(page, 1200)
    mark('zalogowany')
    await moveTo(page, 700, 372, { pause: 700 })
    await moveTo(page, 960, 141, { pause: 600 })
    await moveTo(page, 900, 500, { pause: 900 })
    await settle(page, 600)
    // Token zapisujemy, żeby kolejne rozdziały startowały już zalogowane.
    await saveStorage(scene.context, STATE)
  })
}

/* ------------------------------------------------- 03: działka, uprawa, wynik */

if (TAKE === 'all' || TAKE === '03-analiza') {
  await take('03-analiza', browser, { url: '/', ...AUTH }, async (page, scene) => {
    await stageLoading(page, { polls: 3, delayMs: 1200 })
    await settle(page, 1200)
    mark('pole')
    await moveTo(page, 960, 416, { pause: 600 })
    await pickParcelOnCamera(page)
    mark('uprawa')
    await settle(page, 700)
    await confirmCropOnCamera(page)
    mark('ladowanie')
    await settle(page, 1300)
    await moveTo(page, 960, 560, { pause: 700 })
    await settle(page, 2200)
    await moveTo(page, 960, 640, { pause: 700 })

    // Wynik: plakietka ryzyka, „W skrócie”, przyczyny, bilans wodny i wykres lat.
    await page.getByRole('heading', { name: 'Twój raport' }).first().waitFor({ timeout: 40000 })
    await settle(page, 900)
    await reveal(page, page.getByRole('heading', { name: 'Twój raport' }).first(), { at: 0.22 })
    await settle(page, 700)
    mark('raport')
    await moveTo(page, 746, 285, { pause: 700 })
    await moveTo(page, 700, 331, { pause: 900 })
    await moveTo(page, 713, 500, { pause: 700 })
    mark('przyczyny')
    await settle(page, 700)
    await moveTo(page, 1180, 560, { pause: 900 })
    mark('bilans')
    await settle(page, 900)
    await moveTo(page, 1211, 600, { pause: 1000 })
    await settle(page, 600)
    await saveStorage(scene.context, STATE)
  })
}

/* --------------------------------------------------- 04: „Jak doszło do tej…" */

if (TAKE === 'all' || TAKE === '04-wykresy') {
  await take('04-wykresy', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.history-chart'), { at: 0.24 })
    await settle(page, 700)
    mark('historia')
    // Woda w glebie: zejście do progu stresu i dalszy ciąg scenariuszy po prawej.
    await moveTo(page, 660, 160, { pause: 700 })
    await moveTo(page, 1140, 210, { pause: 900 })
    await settle(page, 1400)
    mark('opad')
    // Opad i parowanie dzień po dniu.
    await moveTo(page, 760, 420, { pause: 600 })
    await moveTo(page, 1160, 470, { pause: 900 })
    await settle(page, 1600)
  })
}

/* ------------------------------------------- 05: „Co dalej: najbliższe 30 dni" */

if (TAKE === 'all' || TAKE === '05-scenariusze') {
  await take('05-scenariusze', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.scenarios'), { at: 0.24 })
    await settle(page, 700)
    mark('scenariusze')
    await moveTo(page, 963, 100, { pause: 700 })
    await moveTo(page, 1140, 108, { pause: 900 })
    await settle(page, 1000)
    mark('scen-wykres')
    // Pasmo scenariuszy: od suchych do mokich, z progiem stresu.
    await moveTo(page, 700, 330, { pause: 700 })
    await moveTo(page, 1180, 380, { pause: 900 })
    await settle(page, 1600)
  })
}

/* ------------------------------------------------ 06: „Co da retencja na tej…" */

if (TAKE === 'all' || TAKE === '06-retencja') {
  await take('06-retencja', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.whatif'), { at: 0.24 })
    await settle(page, 700)
    mark('retencja')
    await moveTo(page, 963, 100, { pause: 600 })
    await moveTo(page, 963, 175, { pause: 900 })
    await settle(page, 900)
    mark('ulewy')
    await moveTo(page, 700, 180, { pause: 600 })
    await moveTo(page, 1150, 185, { pause: 900 })
    await settle(page, 800)
    mark('srodki')
    await moveTo(page, 620, 300, { pause: 700 })
    await moveTo(page, 1290, 360, { pause: 900 })
    await settle(page, 1600)
  })
}

/* ------------------------------------------------------------ 07: zalecenia */

if (TAKE === 'all' || TAKE === '07-zalecenia') {
  await take('07-zalecenia', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.rec-table thead'), { at: 0.18 })
    await settle(page, 700)
    mark('tabela')
    await moveTo(page, 587, 200, { pause: 700 })
    await moveTo(page, 1000, 250, { pause: 900 })
    await settle(page, 700)
    // Druga grupa: agrotechnika.
    await scrollBy(page, 430, { settleMs: 1400 })
    mark('agro')
    await moveTo(page, 587, 300, { pause: 700 })
    await moveTo(page, 1000, 340, { pause: 900 })
    await settle(page, 700)
    // Trzecia grupa: nawadnianie na końcu.
    await scrollBy(page, 430, { settleMs: 1400 })
    mark('nawadnianie')
    await moveTo(page, 587, 340, { pause: 700 })
    await moveTo(page, 1000, 380, { pause: 900 })
    await settle(page, 1400)
  })
}

/* -------------------------------------------------------------- 08: asystent */

if (TAKE === 'all' || TAKE === '08-asystent') {
  await take('08-asystent', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.chat'), { at: 0.26 })
    await settle(page, 700)
    mark('czat')
    await moveTo(page, 963, 590, { pause: 600 })

    // Pytanie z listy podpowiedzi.
    const chip = page.locator('.chat-suggest button').filter({ hasText: 'Co powinienem zrobić najpierw?' }).first()
    await moveTo(page, 963, 661, { pause: 800 })
    mark('pytanie1')
    await clickAt(page, chip, { x: 0, y: 0 }, 1600)
    await settle(page, 600)
    await moveTo(page, 1200, 700, { pause: 700 })
    mark('pisze1')
    await settle(page, 1200)
    await page.locator('.chat-msg.pending').first().waitFor({ state: 'detached', timeout: 20000 }).catch(() => {})
    await settle(page, 1000)
    mark('odpowiedz1')
    await moveTo(page, 700, 500, { pause: 700 })
    await moveTo(page, 1180, 560, { pause: 900 })
    await scrollPage(page, await page.evaluate(() => window.scrollY + 120), { settleMs: 1100 })
    await settle(page, 900)

    // Własne pytanie o zgodę na wał.
    await moveTo(page, 700, 640, { pause: 700 })
    await ensureVisible(page, page.locator('.chat-form input'))
    await typeInto(page, page.locator('.chat-form input'), 'Czy muszę mieć zgodę na wał?', { perChar: [60, 130] })
    mark('pytanie2')
    await clickAt(page, page.getByRole('button', { name: 'Wyślij' }), { x: 0, y: 0 }, 1400)
    await settle(page, 800)
    await page.locator('.chat-msg.pending').first().waitFor({ state: 'detached', timeout: 20000 }).catch(() => {})
    await settle(page, 1000)
    mark('odpowiedz2')
    await scrollPage(page, await page.evaluate(() => window.scrollY + 260), { settleMs: 1300 })
    await settle(page, 700)
    await moveTo(page, 900, 700, { pause: 900 })
    await settle(page, 900)
  })
}

/* --------------------------------------------------- 09: druk i zapis raportu */

if (TAKE === 'all' || TAKE === '09-druk') {
  await take('09-druk', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await reveal(page, page.locator('.panel-footer').last(), { at: 0.72 })
    await settle(page, 700)
    mark('stopka')
    await moveTo(page, 1294, 871, { pause: 900 })
    await clickAt(page, page.getByRole('button', { name: 'Drukuj' }).first(), { x: 0, y: 0 }, 1800)
    mark('druk')
    await settle(page, 700)
    await moveTo(page, 1398, 871, { pause: 900 })
    await clickAt(page, page.getByRole('button', { name: 'Pobierz' }).first(), { x: 0, y: 0 }, 1600)
    mark('pobierz')
    await settle(page, 1200)
  })
}

/* ------------------------------------------- 10: raport do wydruku (Chrome PDF) */

if (TAKE === 'all' || TAKE === '10-wydruk') {
  await take('10-wydruk', browser, { url: PRINT_URL }, async (page) => {
    await settle(page, 1600)
    mark('druk-gora')
    await moveTo(page, 960, 300, { pause: 700 })
    await reveal(page, page.getByRole('heading', { name: /1\. Ocena sytuacji wodnej/i }).first(), { at: 0.14 })
    mark('druk-ocena')
    await moveTo(page, 960, 300, { pause: 700 })
    await reveal(page, page.getByRole('heading', { name: /Woda w glebie: ostatnie miesiące/i }).first(), { at: 0.12 })
    mark('druk-wykresy')
    await moveTo(page, 900, 420, { pause: 700 })
    await settle(page, 900)
    await reveal(page, page.getByRole('heading', { name: /Ten rok na tle poprzednich lat/i }).first(), { at: 0.12 })
    mark('druk-lata')
    await moveTo(page, 960, 380, { pause: 700 })
    await settle(page, 1400)
  })
}

/* ------------------------------------------- 11: profil i historia raportów */

if (TAKE === 'all' || TAKE === '11-profil') {
  await take('11-profil', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1000)
    await loadDemo(page)
    await scrollToTop(page, { settleMs: 800 })
    await clickAt(page, page.getByRole('button', { name: 'Twoje raporty' }), { x: 0, y: 0 }, 1800)
    await settle(page, 1200)
    mark('profil')
    await moveTo(page, 760, 208, { pause: 700 })
    await moveTo(page, 1180, 340, { pause: 800 })
    await settle(page, 600)
    mark('historia')
    await moveTo(page, 1100, 420, { pause: 700 })
    await moveTo(page, 1420, 422, { pause: 900 })
    await settle(page, 700)
    await moveTo(page, 960, 420, { pause: 900 })
    await settle(page, 1200)
  })
}

/* ---------------------------------------------- 12: wylogowanie i powrót na start */

if (TAKE === 'all' || TAKE === '12-powrot') {
  await take('12-powrot', browser, { url: '/', ...AUTH }, async (page) => {
    await settle(page, 1200)
    mark('app')
    await moveTo(page, 960, 416, { pause: 700 })
    await moveTo(page, 1820, 38, { pause: 700 })
    mark('wyloguj')
    await clickAt(page, page.getByRole('button', { name: 'Wyloguj' }), { x: 0, y: 0 }, 1800)
    await page.getByRole('heading', { name: /Zatrzymaj wodę/i }).first().waitFor({ timeout: 20000 })
    await settle(page, 1400)
    await scrollToTop(page, { settleMs: 900 })
    mark('logo')
    await moveTo(page, 716, 500, { pause: 900 })
    await moveTo(page, 1100, 560, { pause: 900 })
    await settle(page, 1200)
  })
}

await browser.close()
console.log('koniec')
