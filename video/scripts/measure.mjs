import { launch, openScene, settle, login, reveal, clickAt, center, scrollToTop, typeInto, typeDate, BASE } from './lib.mjs'

/**
 * Mierzy, gdzie naprawdę leży sekcja albo karta, żeby kamera w montażu celowała
 * w treść, a nie w puste tło. Współrzędne są w układzie nagrania 1920×1080,
 * mierzone w takim stanie ekranu, w jakim zobaczy go montaż (po przewinięciu).
 */
const browser = await launch()

const probe = async (label, locator) => {
  const rect = await locator.boundingBox().catch(() => null)
  if (!rect) {
    console.log(`${label.padEnd(30)} brak`)
    return
  }
  console.log(
    `${label.padEnd(30)} center=${Math.round(rect.x + rect.width / 2)},${Math.round(rect.y + rect.height / 2)}` +
      `  box=[${Math.round(rect.x)},${Math.round(rect.y)},${Math.round(rect.width)},${Math.round(rect.height)}]`,
  )
}

const scrollY = (page) => page.evaluate(() => Math.round(window.scrollY))

/* ------------------------------------------------------------ strona startowa */
{
  const scene = await openScene(browser, 'probe-start', { url: '/' })
  const { page } = scene
  await settle(page, 1200)

  await probe('hero h1', page.getByRole('heading', { name: /Zatrzymaj wodę/i }).first())
  await probe('karta logowania', page.locator('.lp-auth'))
  await probe('hero eyebrow', page.locator('.lp-hero .eyebrow').first())

  const stats = page.getByRole('heading', { name: /Za suszę płacimy po fakcie/i }).first()
  await reveal(page, stats, { at: 0.32 })
  console.log(`  scrollY=${await scrollY(page)}`)
  await probe('liczby h2', stats)
  await probe('liczby siatka', page.locator('.lp-stats'))

  const pitch = page.getByRole('heading', { name: /Rolnik zna swoje pole/i }).first()
  await reveal(page, pitch, { at: 0.34 })
  console.log(`  scrollY=${await scrollY(page)}`)
  await probe('pitch h2', pitch)
  await probe('podglad raportu', page.locator('.lp-preview'))

  const steps = page.getByRole('heading', { name: /Od diagnozy do działania/i }).first()
  await reveal(page, steps, { at: 0.3 })
  console.log(`  scrollY=${await scrollY(page)}`)
  await probe('kroki h2', steps)
  await probe('kroki siatka', page.locator('.lp-steps'))

  const sources = page.getByRole('heading', { name: /Pięć źródeł danych/i }).first()
  await reveal(page, sources, { at: 0.3 })
  console.log(`  scrollY=${await scrollY(page)}`)
  await probe('zrodla h2', sources)
  await probe('zrodla siatka', page.locator('.lp-sources'))

  const model = page.getByRole('heading', { name: /Darmowe dla rolnika/i }).first()
  await reveal(page, model, { at: 0.3 })
  console.log(`  scrollY=${await scrollY(page)}`)
  await probe('model h2', model)
  await probe('model karty', page.locator('.lp-model'))
  await probe('roadmap', page.locator('.lp-roadmap'))

  await scrollToTop(page, { settleMs: 1200 })
  console.log(`  powrot scrollY=${await scrollY(page)}`)

  await scene.context.close()
}

/* --------------------------------------------------------- aplikacja po logowaniu */
{
  const scene = await openScene(browser, 'probe-app', { url: '/' })
  const { page } = scene
  await login(page, { route: '/' })

  await scrollToTop(page, { settleMs: 900 })
  await probe('topbar', page.locator('.topbar'))
  await probe('eyebrow dzien dobry', page.locator('.eyebrow').first())
  await probe('krok1 h1', page.getByRole('heading', { name: /Gdzie jest Twoje pole/i }).first())
  await probe('stepper', page.locator('.stepper'))
  await probe('panel numer', page.locator('.grid-2 .panel').nth(0))
  await probe('panel mapa', page.locator('.grid-2 .panel').nth(1))
  await probe('input numer', page.locator('input[placeholder^="np. 141201"]'))
  await probe('przycisk znajdz', page.getByRole('button', { name: 'Znajdź działkę' }))
  await probe('link demo', page.getByText(/Zobacz przykładowe pole/i).first())

  // Krok 1: wpisujemy numer i szukamy.
  await typeInto(page, page.locator('input[placeholder^="np. 141201"]'), '101609_2.0011.352')
  await clickAt(page, page.getByRole('button', { name: 'Znajdź działkę' }), { x: 0, y: 0 }, 1600)
  await settle(page, 900)
  console.log(`  po wyborze dzialki scrollY=${await scrollY(page)}`)
  await probe('krok2 h2', page.getByRole('heading', { name: /Co rośnie na tym polu/i }).first())
  await probe('krok2 panel', page.locator('.section .panel').nth(2))
  await probe('kafle upraw', page.locator('.crop-grid'))
  await probe('kafl pszenica', page.locator('.crop-tile.selected'))
  await probe('pole daty', page.locator('input[type="date"]'))
  await probe('stopka zatwierdz', page.getByRole('button', { name: 'Zatwierdź wybór' }))

  // Data z zadania demo: z nią wynik jest gotowy w katalogu demo/, więc liczy się od razu.
  await typeDate(page, page.locator('input[type="date"]'), '2026-06-15')
  await clickAt(page, page.getByRole('button', { name: 'Zatwierdź wybór' }), { x: 0, y: 0 }, 1200)
  await page.getByRole('heading', { name: 'Twój raport' }).first().waitFor({ timeout: 30000 })
  await settle(page, 900)
  await scrollToTop(page, { settleMs: 900 })
  console.log(`  raport scrollY=${await scrollY(page)}`)

  const raport = page.getByRole('heading', { name: 'Twój raport' }).first()
  await reveal(page, raport, { at: 0.22 })
  console.log(`  raport scrollY=${await scrollY(page)}`)
  await probe('raport h2', raport)
  await probe('plakietka', page.locator('.badge').first())
  await probe('w skrocie', page.getByText('W skrócie:').first())
  await probe('przyczyny karta', page.locator('.step-card').nth(0))
  await probe('bilans karta', page.locator('.step-card').nth(1))
  await probe('years chart', page.locator('.years-chart'))

  const history = page.locator('.history-chart')
  await reveal(page, history, { at: 0.24 })
  console.log(`  historia scrollY=${await scrollY(page)}`)
  await probe('historia karta', history)
  await probe('wykres woda', history.locator('.chart').nth(0))
  await probe('wykres opad', history.locator('.chart').nth(1))

  const scen = page.locator('.scenarios')
  await reveal(page, scen, { at: 0.24 })
  console.log(`  scenariusze scrollY=${await scrollY(page)}`)
  await probe('scenariusze karta', scen)
  await probe('scen stats', page.locator('.scen-stats'))
  await probe('scen wykres', scen.locator('svg'))

  const whatif = page.locator('.whatif')
  await reveal(page, whatif, { at: 0.24 })
  console.log(`  whatif scrollY=${await scrollY(page)}`)
  await probe('whatif karta', whatif)
  await probe('whatif ulewy', page.locator('.whatif-storms'))
  await probe('whatif srodki', page.locator('.whatif-measures'))

  const table = page.locator('.rec-table')
  await reveal(page, table, { at: 0.3 })
  console.log(`  tabela scrollY=${await scrollY(page)}`)
  await probe('tabela zalecen', table)
  await probe('tabela naglowek', page.locator('.rec-table thead'))
  await probe('tabela kategoria', page.locator('.rec-cat').first())

  const chat = page.locator('.chat')
  await reveal(page, chat, { at: 0.28 })
  console.log(`  czat scrollY=${await scrollY(page)}`)
  await probe('czat', chat)
  await probe('czat naglowek', page.locator('.chat-head'))
  await probe('czat podpowiedzi', page.locator('.chat-suggest'))
  await probe('czat pole', page.locator('.chat-form input'))

  // Stopka raportu: Drukuj / Pobierz.
  const footer = page.locator('.panel-footer').last()
  await reveal(page, footer, { at: 0.7 })
  console.log(`  stopka scrollY=${await scrollY(page)}`)
  await probe('stopka raportu', footer)
  await probe('drukuj', page.getByRole('button', { name: 'Drukuj' }).first())
  await probe('pobierz', page.getByRole('button', { name: 'Pobierz' }).first())

  // Profil: historia raportów (analiza zapisała się, bo byliśmy zalogowani).
  await clickAt(page, page.getByRole('button', { name: 'Twoje raporty' }), { x: 0, y: 0 }, 1600)
  await settle(page, 1200)
  await scrollToTop(page, { settleMs: 800 })
  await probe('profil h1', page.getByRole('heading', { name: /Dzień dobry/i }).first())
  await probe('historia lista', page.locator('.history-list'))
  await probe('historia wpis', page.locator('.history-item').first())

  await scene.context.close()
}

/* --------------------------------------------------- raport do druku (PDF/HTML) */
{
  const scene = await openScene(browser, 'probe-print', {
    url: '/api/v1/analyses/demo-lazisko_352_2026_06_15/raport',
  })
  const { page } = scene
  await settle(page, 1400)
  const size = await page.evaluate(() => ({
    w: document.documentElement.scrollWidth,
    h: document.documentElement.scrollHeight,
  }))
  console.log(`raport do druku strona ${JSON.stringify(size)}`)
  const headings = await page.evaluate(() =>
    [...document.querySelectorAll('h1,h2,h3')].slice(0, 12).map((h) => h.textContent.trim().slice(0, 60)),
  )
  console.log('  naglowki:', JSON.stringify(headings, null, 1))
  await scene.context.close()
}

await browser.close()
console.log('gotowe')
