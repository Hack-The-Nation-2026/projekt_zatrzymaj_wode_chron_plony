import { mkdir } from 'node:fs/promises'
import { launch, openScene, settle, reveal, scrollToTop, ensureLoginState } from './lib.mjs'
import { askAssistant, confirmCropOnCamera, loadDemo, pickParcelOnCamera, stageLoading, waitForReport } from './app.mjs'

/**
 * Zrzuty kontrolne ekranów, które wchodzą do filmu. Służą do sprawdzenia kadru
 * i współrzędnych kamery, a nie do publikacji. Lądują w `out/check/`.
 */
const OUT = 'out/check'
const STATE = 'public/clips/state-login.json'

const browser = await launch()
await mkdir(OUT, { recursive: true })
const shot = async (page, name) => {
  await page.screenshot({ path: `${OUT}/${name}.png` })
  console.log(`✓ ${name}.png`)
}
const loggedIn = await ensureLoginState(browser, STATE)
console.log(loggedIn ? 'konto: stan zapisany' : '! nie udało się zalogować')

/* ------------------------------------------------------------ strona startowa */
{
  const scene = await openScene(browser, 'shot-start', { url: '/' })
  const { page } = scene
  await settle(page, 1600)
  await shot(page, '01-hero')
  await reveal(page, page.getByRole('heading', { name: /Za suszę płacimy po fakcie/i }).first(), { at: 0.32 })
  await shot(page, '02-liczby')
  await reveal(page, page.getByRole('heading', { name: /Od diagnozy do działania/i }).first(), { at: 0.3 })
  await shot(page, '03-kroki')
  await reveal(page, page.getByRole('heading', { name: /Pięć źródeł danych/i }).first(), { at: 0.3 })
  await shot(page, '04-zrodla')
  await reveal(page, page.getByRole('heading', { name: /Darmowe dla rolnika/i }).first(), { at: 0.3 })
  await shot(page, '05-model')
  await scene.context.close()
}

/* ------------------------------------------------------------------ aplikacja */
{
  const scene = await openScene(browser, 'shot-app', { url: '/', storage: STATE })
  const { page } = scene
  await stageLoading(page, { polls: 3 })
  await settle(page, 1200)
  await shot(page, '06-krok1')

  await pickParcelOnCamera(page)
  await shot(page, '07-krok2')

  await confirmCropOnCamera(page)
  await settle(page, 900)
  await shot(page, '08-ladowanie')
  await settle(page, 1600)
  await shot(page, '09-ladowanie-pozniej')

  await waitForReport(page)
  await shot(page, '10-raport-gora')
  await reveal(page, page.locator('.history-chart'), { at: 0.24 })
  await shot(page, '11-historia')
  await reveal(page, page.locator('.scenarios'), { at: 0.24 })
  await shot(page, '12-scenariusze')
  await reveal(page, page.locator('.whatif'), { at: 0.24 })
  await shot(page, '13-whatif')
  await reveal(page, page.locator('.rec-table'), { at: 0.3 })
  await shot(page, '14-zalecenia')
  await reveal(page, page.locator('.chat'), { at: 0.26 })
  await shot(page, '15-czat')
  await askAssistant(page, { suggestion: 'Co powinienem zrobić najpierw?' })
  await shot(page, '16-czat-odpowiedz')
  await askAssistant(page, { question: 'Czy muszę mieć zgodę na wał?' })
  await shot(page, '17-czat-odpowiedz2')

  const footer = page.locator('.panel-footer').last()
  await reveal(page, footer, { at: 0.72 })
  await shot(page, '18-stopka')

  await scrollToTop(page, { settleMs: 600 })
  const topbar = page.getByRole('button', { name: 'Twoje raporty' })
  await topbar.click()
  await settle(page, 1400)
  await shot(page, '19-profil')
  await scene.context.close()
}

/* -------------------------------------------------------- raport do druku (A4) */
{
  const scene = await openScene(browser, 'shot-print', {
    url: '/api/v1/analyses/demo-lazisko_352_2026_06_15/raport',
  })
  const { page } = scene
  await settle(page, 1600)
  await shot(page, '20-wydruk-gora')
  await page.evaluate(() => window.scrollTo({ top: window.innerHeight * 1.6, behavior: 'instant' }))
  await settle(page, 700)
  await shot(page, '21-wydruk-srodek')
  await scene.context.close()
}

/* ------------------------------------------------------ szybka droga (loadDemo) */
{
  const scene = await openScene(browser, 'shot-demo', { url: '/', storage: STATE })
  const { page } = scene
  await loadDemo(page)
  await shot(page, '22-demo-raport')
  await scene.context.close()
}

await browser.close()
console.log('gotowe')
