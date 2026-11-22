import { clickAt, ensureVisible, settle, typeDate, typeInto, reveal, scrollToTop } from './lib.mjs'

/**
 * Wspólne przejścia po aplikacji Wodnika. Nagranie i zrzuty ekranu korzystają
 * z tych samych kroków, żeby zrzut pokazywał dokładnie ten stan, który trafi do filmu.
 */

export const DEMO = { id: '101609_2.0011.352', date: '2026-06-15', crop: 'Pszenica ozima' }

/**
 * Szybka droga do raportu: link „Zobacz przykładowe pole w Łazisku” wypełnia numer
 * działki, uprawę i datę, a wynik dla tego zestawu leży gotowy w katalogu demo/.
 * Używamy jej w ujęciach, w których sam wybór działki jest już nieistotny.
 */
export async function loadDemo(page, { settleMs = 1100 } = {}) {
  await scrollToTop(page, { settleMs: 600 })
  await clickAt(page, page.getByText(/Zobacz przykładowe pole/i).first(), { x: -40, y: 0 }, 1800)
  const confirm = page.getByRole('button', { name: 'Zatwierdź wybór' })
  await confirm.waitFor({ state: 'visible', timeout: 25000 })
  await ensureVisible(page, confirm)
  await clickAt(page, confirm, { x: 0, y: 0 }, 1200)
  await page.getByRole('heading', { name: 'Twój raport' }).first().waitFor({ timeout: 40000 })
  await settle(page, settleMs)
}

/**
 * Spowalnia analizę działki demo tak, żeby na nagraniu było widać prawdziwy ekran
 * postępu. Wynik demo jest gotowy od razu, więc bez tego ekran „Sprawdzamy Twoje
 * pole…” mrugnąłby tylko jednym kadrem. Podmieniamy wyłącznie stan zadania na
 * „running” i rozkładamy etapy w czasie; treść postępu i raport są prawdziwe.
 */
export async function stageLoading(page, { polls = 3, delayMs = 1200 } = {}) {
  await page.route('**/api/v1/analyses', async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    await settle(page, 700)
    await route.fulfill({ response, json: { ...body, status: 'running' } })
  })
  let count = 0
  await page.route('**/api/v1/analyses/*', async (route) => {
    const response = await route.fetch()
    const body = await response.json()
    const steps = (body.progress ?? []).map((step) => ({ ...step, state: 'pending' }))
    count += 1
    if (count <= polls) {
      const index = Math.min(count - 1, steps.length - 1)
      steps.forEach((step, i) => {
        step.state = i < index ? 'done' : i === index ? 'running' : 'pending'
      })
      await settle(page, delayMs)
      return route.fulfill({ response, json: { ...body, status: 'running', progress: steps } })
    }
    return route.fulfill({ response, json: body })
  })
}

/** Krok 1 i 2 oglądane w filmie: numer działki, uprawa i data. */
export async function pickParcelOnCamera(page) {
  const input = page.locator('input[placeholder^="np. 141201"]')
  await typeInto(page, input, DEMO.id, { perChar: [70, 150] })
  await clickAt(page, page.getByRole('button', { name: 'Znajdź działkę' }), { x: 0, y: 0 }, 1900)
  const panel = page.getByRole('heading', { name: /Co rośnie na tym polu/i }).first()
  await panel.waitFor({ state: 'visible', timeout: 25000 })
  await settle(page, 1000)
}

/** Krok 2: klikamy kafel pszenicy, ustawiamy datę i zatwierdzamy wybór. */
export async function confirmCropOnCamera(page) {
  const tile = page.locator('.crop-tile').filter({ hasText: DEMO.crop }).first()
  await clickAt(page, tile, { x: -60, y: 0 }, 1200)
  await typeDate(page, page.locator('input[type="date"]'), DEMO.date)
  await clickAt(page, page.getByRole('button', { name: 'Zatwierdź wybór' }), { x: 0, y: 0 }, 1000)
}

/** Czeka, aż raport się pokaże, i ustawia początek raportu w kadrze. */
export async function waitForReport(page, { at = 0.22 } = {}) {
  await page.getByRole('heading', { name: 'Twój raport' }).first().waitFor({ timeout: 40000 })
  await settle(page, 900)
  await reveal(page, page.getByRole('heading', { name: 'Twój raport' }).first(), { at })
  await settle(page, 500)
}

/** Jedno pytanie do asystenta: podpowiedź z listy albo własne zdanie. */
export async function askAssistant(page, { suggestion, question, waitMs = 12000 } = {}) {
  if (suggestion) {
    const chip = page.locator('.chat-suggest button').filter({ hasText: suggestion }).first()
    await clickAt(page, chip, { x: 0, y: 0 }, 1400)
  } else {
    const input = page.locator('.chat-form input')
    await typeInto(page, input, question, { perChar: [65, 140] })
    await clickAt(page, page.getByRole('button', { name: 'Wyślij' }), { x: 0, y: 0 }, 1000)
  }
  // Czekamy na koniec pisania asystenta, a nie na sztywny czas.
  await page.locator('.chat-msg.pending').first().waitFor({ state: 'visible', timeout: 8000 }).catch(() => {})
  await page.locator('.chat-msg.pending').first().waitFor({ state: 'detached', timeout: waitMs }).catch(() => {})
  await settle(page, 900)
}
