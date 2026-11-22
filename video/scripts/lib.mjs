import { chromium } from 'playwright'
import { mkdir, rm } from 'node:fs/promises'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import path from 'node:path'

const run = promisify(execFile)

export const CHROME = '/home/mati/.local/share/chrome-mcp/chrome-linux64/chrome'
// Adres serwisu do nagrania. Wodnik podaje zbudowany frontend z FastAPI na :8000,
// więc nagrywamy dokładnie to, co zobaczy jury, bez osobnego serwera deweloperskiego.
export const BASE = process.env.DEMO_BASE ?? 'http://localhost:8000'
export const OUT = path.resolve('public/clips')

export const ACCOUNT = {
  email: process.env.WODNIK_EMAIL ?? 'film@wodnik.test',
  password: process.env.WODNIK_PASSWORD ?? 'wodnik-film-2026',
  name: 'Grzegorz',
}

/**
 * Wszystko, co musi przetrwać każdą nawigację, wstrzykujemy skryptem startowym:
 * kursor rysowany w DOM i wyłączenie animacji, które psują ujęcia.
 * Zwykły <style> dodany raz po wejściu na stronę ginie przy pierwszym przeładowaniu.
 */
const BOOT_SCRIPT = () => {
  const style = document.createElement('style')
  style.textContent = `
    /* Kursor systemowy chowamy: w kadrze ma być tylko nasz rysowany. */
    * { cursor: none !important; }
  `
  const installStyle = () => {
    if (document.head && !document.head.querySelector('#demo-hide')) {
      style.id = 'demo-hide'
      document.head.appendChild(style)
    }
  }

  if (window.__cursorReady) {
    installStyle()
    return
  }
  window.__cursorReady = true

  const mount = () => {
    installStyle()
    const root = document.body
    if (!root) return
    const cursorStyle = document.createElement('style')
    // Kursor na ciemnym tle serwisu: biały grot z granatowym obrysem, a fala
    // kliknięcia w kolorze wody (paleta Wodnika), więc widać ją na granacie.
    cursorStyle.textContent = `
      #demo-cursor, #demo-ripple {
        position: fixed; left: 0; top: 0; z-index: 2147483647;
        pointer-events: none; will-change: transform;
      }
      #demo-cursor { width: 32px; height: 32px; filter: drop-shadow(0 3px 5px rgba(4,12,20,.55)); }
      #demo-ripple {
        width: 48px; height: 48px; margin: -24px 0 0 -24px; border-radius: 999px;
        border: 3px solid rgba(74,163,232,.75); background: rgba(74,163,232,.18);
        opacity: 0; transform: scale(.2);
      }
      #demo-ripple.ping { animation: demo-ping .55s cubic-bezier(.2,.7,.3,1) forwards; }
      @keyframes demo-ping {
        0% { opacity: .95; transform: scale(.25); }
        100% { opacity: 0; transform: scale(1.45); }
      }
    `
    const cursor = document.createElement('div')
    cursor.id = 'demo-cursor'
    cursor.innerHTML = `<svg viewBox="0 0 32 32" width="32" height="32">
      <path d="M4.5 2.4 L27 16.2 L16.4 17.8 L12 28.2 Z"
        fill="#ffffff" stroke="#0b1c2a" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>`
    const ripple = document.createElement('div')
    ripple.id = 'demo-ripple'
    root.appendChild(cursorStyle)
    root.appendChild(cursor)
    root.appendChild(ripple)

    const target = { x: window.innerWidth * 0.5, y: window.innerHeight * 0.55 }
    const current = { ...target }
    let pressed = false

    const draw = () => {
      cursor.style.transform = `translate3d(${current.x - 5}px, ${current.y - 3}px, 0) scale(${pressed ? 0.86 : 1})`
      ripple.style.left = `${current.x}px`
      ripple.style.top = `${current.y}px`
    }
    draw()

    const loop = () => {
      const ease = pressed ? 0.55 : 0.32
      current.x += (target.x - current.x) * ease
      current.y += (target.y - current.y) * ease
      draw()
      requestAnimationFrame(loop)
    }
    requestAnimationFrame(loop)

    window.addEventListener('mousemove', (event) => {
      target.x = event.clientX
      target.y = event.clientY
    }, { capture: true, passive: true })

    window.addEventListener('mousedown', (event) => {
      target.x = event.clientX
      target.y = event.clientY
      pressed = true
      ripple.classList.remove('ping')
      void ripple.offsetWidth
      ripple.classList.add('ping')
    }, { capture: true, passive: true })

    window.addEventListener('mouseup', () => { pressed = false }, { capture: true, passive: true })
  }

  if (document.body) mount()
  else document.addEventListener('DOMContentLoaded', mount, { once: true })
}

/** Kursor pamiętamy między wywołaniami, żeby każdy ruch zaczynał się tam, gdzie skończył poprzedni. */
export const cursor = { x: 1280, y: 700 }

const random = (min, max) => min + Math.random() * (max - min)
const sleep = (page, ms) => page.waitForTimeout(ms)

export async function launch() {
  await mkdir(OUT, { recursive: true })
  return chromium.launch({
    executablePath: CHROME,
    args: ['--hide-scrollbars', '--force-color-profile=srgb', '--font-render-hinting=none'],
  })
}

export async function openScene(browser, name, { width = 1920, height = 1080, url = '/', storage = null } = {}) {
  await rm(path.join(OUT, `${name}.mp4`), { force: true })
  const context = await browser.newContext({
    viewport: { width, height },
    deviceScaleFactor: 1,
    reducedMotion: 'no-preference',
    locale: 'pl-PL',
    timezoneId: 'Europe/Warsaw',
    acceptDownloads: true,
    recordVideo: { dir: OUT, size: { width, height } },
    storageState: storage ?? undefined,
  })
  const page = await context.newPage()
  await page.addInitScript(BOOT_SCRIPT)
  page.on('console', (msg) => {
    if (msg.type() === 'error') console.log(`  [console] ${msg.text()}`)
  })
  page.on('pageerror', (error) => console.log(`  [pageerror] ${error.message}`))
  cursor.x = width * 0.66
  cursor.y = height * 0.65
  await page.goto(`${BASE}${url}`, { waitUntil: 'networkidle' })
  await settle(page, 500)
  // Kursor musi wystartować dokładnie tam, gdzie myśli nasz licznik.
  await page.mouse.move(cursor.x, cursor.y)
  return { context, page, video: page.video(), name, width, height }
}

export async function finishScene(scene) {
  const { context, video, name } = scene
  await context.close()
  const source = await video.path()
  const target = path.join(OUT, `${name}.mp4`)
  // Playwright nagrywa WebM z VP9. Samo przemianowanie pliku na .mp4 zostawiało
  // kontener Matroski pod rozszerzeniem MP4 i przeglądarka renderująca zrywała
  // połączenie z kompozytorem przy kilku nagraniach naraz. Przekodowujemy więc
  // na H.264, który Chromium dekoduje lekko.
  await run('ffmpeg', [
    '-v', 'error', '-y', '-i', source,
    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
    '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', target,
  ])
  await rm(source, { force: true })
}

export const settle = sleep

/**
 * Ruch myszy po łuku z nierównym tempem: kilka punktów po krzywej Béziera,
 * przystanki w środku drogi i chwila namysłu na końcu. Prosta linia zdradza skrypt.
 */
export async function moveTo(page, x, y, { curve = 0.16, pause = 260, jitter = 2 } = {}) {
  const from = { x: cursor.x, y: cursor.y }
  const to = { x, y }
  const dx = to.x - from.x
  const dy = to.y - from.y
  const distance = Math.hypot(dx, dy)
  if (distance < 3) {
    cursor.x = to.x
    cursor.y = to.y
    if (pause) await sleep(page, pause)
    return
  }

  // Punkt kontrolny przesunięty w bok, więc droga jest łukiem, nie odcinkiem.
  const bow = distance * curve * random(-1, 1)
  const nx = -dy / distance
  const ny = dx / distance
  const control = {
    x: (from.x + to.x) / 2 + nx * bow,
    y: (from.y + to.y) / 2 + ny * bow,
  }

  const steps = Math.max(14, Math.min(48, Math.round(distance / 14)))
  for (let index = 1; index <= steps; index += 1) {
    const t = index / steps
    // Wyhamowanie na końcu: ostatnie kroki są krótsze, więc kliknięcie nie jest szarpnięciem.
    const eased = t < 0.85 ? t * 0.94 : 0.799 + (t - 0.85) * 1.34
    const u = 1 - eased
    const px = u * u * from.x + 2 * u * eased * control.x + eased * eased * to.x
    const py = u * u * from.y + 2 * u * eased * control.y + eased * eased * to.y
    await page.mouse.move(px, py)
    // Nierówne odstępy: raz dłuższa pauza, raz krótsza, jak przy prowadzeniu ręki.
    if (index % 3 === 0) await sleep(page, random(3, 11))
  }

  cursor.x = to.x
  cursor.y = to.y

  if (jitter) {
    // Drobna korekta na koniec: ręka nie zatrzymuje się idealnie.
    await page.mouse.move(to.x + random(-jitter, jitter), to.y + random(-jitter, jitter))
    await page.mouse.move(to.x, to.y)
  }
  if (pause) await sleep(page, pause)
}

export async function center(locator, offset = { x: 0, y: 0 }) {
  const box = await locator.boundingBox()
  if (!box) throw new Error('Element nie ma ramki')
  return { x: box.x + box.width / 2 + offset.x, y: box.y + box.height / 2 + offset.y }
}

/**
 * Dowozi element do kadru, gdy jest poza widokiem albo schowany pod przyklejonym
 * nagłówkiem. Bez tego klik trafia w pustkę, bo współrzędne poza oknem nie mają adresata.
 * Przewijamy płynnie i tylko wtedy, gdy naprawdę trzeba.
 */
export async function ensureVisible(page, locator, { margin = 110, settleMs = 780 } = {}) {
  const needs = await locator
    .evaluate((element, top) => {
      const rect = element.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) return true
      const fits = rect.height <= window.innerHeight - top - 48
      // Wysoki element nie zmieści się w kadrze, więc wystarczy, że zaczyna się pod nagłówkiem.
      return fits ? rect.top < top || rect.bottom > window.innerHeight - 48 : rect.top < top
    }, margin)
    .catch(() => false)
  if (!needs) return
  await locator.evaluate((element) => {
    const rect = element.getBoundingClientRect()
    const target = window.scrollY + rect.top + rect.height / 2 - window.innerHeight / 2
    window.scrollTo({ top: Math.max(0, Math.round(target)), behavior: 'smooth' })
  })
  await sleep(page, settleMs)
}

/** Kliknięcie z dojściem myszą, krótkim przytrzymaniem i oddechem po nim. */
export async function clickAt(page, locator, offset = { x: 0, y: 0 }, settleMs = 500) {
  await ensureVisible(page, locator)
  const point = await center(locator, offset)
  await moveTo(page, point.x, point.y, { pause: 180 })
  await page.mouse.down()
  await sleep(page, random(70, 120))
  await page.mouse.up()
  if (settleMs) await sleep(page, settleMs)
}

export async function typeInto(page, locator, text, { perChar = [80, 165], settleMs = 300, clear = false } = {}) {
  await ensureVisible(page, locator)
  const point = await center(locator)
  await moveTo(page, point.x, point.y, { pause: 150 })
  await page.mouse.down()
  await sleep(page, random(60, 110))
  await page.mouse.up()
  await sleep(page, 260)
  if (clear) await locator.fill('')
  for (const character of text) {
    // `press` zna tylko nazwy klawiszy, więc polskie znaki wstawiamy jak z klawiatury.
    if (/^[\x20-\x7E]$/.test(character)) await locator.press(character)
    else await page.keyboard.insertText(character)
    await sleep(page, random(perChar[0], perChar[1]))
  }
  if (settleMs) await sleep(page, settleMs)
}

/**
 * Pola daty w Chromium nie przyjmują wpisywania znak po znaku w formacie ISO,
 * więc wypełniamy je od razu, z kliknięciem w pole, żeby na nagraniu było widać,
 * że użytkownik je wybiera.
 */
export async function typeDate(page, locator, value, { settleMs = 400 } = {}) {
  await ensureVisible(page, locator)
  const point = await center(locator)
  await moveTo(page, point.x, point.y, { pause: 180 })
  await page.mouse.down()
  await sleep(page, random(60, 110))
  await page.mouse.up()
  await sleep(page, 280)
  await locator.fill(value)
  await settle(page, 300)
  if (settleMs) await sleep(page, settleMs)
}

/** Przewijanie wyłącznie programowe: kółko na stronie głównej przeskakuje sekcje. */
export async function scrollPage(page, y, { settleMs = 850 } = {}) {
  await page.evaluate((top) => window.scrollTo({ top, behavior: 'smooth' }), y)
  await page.waitForTimeout(settleMs)
}

export async function scrollBy(page, delta, { settleMs = 850 } = {}) {
  await page.evaluate((dy) => window.scrollBy({ top: dy, behavior: 'smooth' }), delta)
  await page.waitForTimeout(settleMs)
}

/** Ustawia element w kadrze (domyślnie w środku) przed pokazaniem go myszą. */
export async function reveal(page, locator, { at = 0.5, settleMs = 850 } = {}) {
  const target = await locator.evaluate((element, fraction) => {
    const rect = element.getBoundingClientRect()
    const wanted = window.scrollY + rect.top + rect.height / 2 - window.innerHeight * fraction
    return Math.max(0, Math.round(wanted))
  }, at)
  await scrollPage(page, target, { settleMs })
}

export async function scrollToTop(page, { settleMs = 700 } = {}) {
  await scrollPage(page, 0, { settleMs })
}

/** Przewija do elementu wolniej, żeby kamera zdążyła za treścią. */
export async function revealBy(page, locator, delta, { settleMs = 900 } = {}) {
  const target = await locator.evaluate((element, dy) => {
    const rect = element.getBoundingClientRect()
    return Math.max(0, Math.round(window.scrollY + rect.top + dy))
  }, delta)
  await scrollPage(page, target, { settleMs })
}

export async function navigate(page, route, { settleMs = 900 } = {}) {
  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(settleMs)
}

/**
 * Logowanie konta z nagłówka strony startowej (karta po prawej). Wypełniamy oba pola
 * myszą i klawiaturą, więc na nagraniu widać prawdziwe logowanie, a nie wstawiony stan.
 */
export async function login(page, { route = '/', settleMs = 1400 } = {}) {
  await page.goto(`${BASE}${route}`, { waitUntil: 'networkidle' })
  await settle(page, 700)
  await typeInto(page, page.locator('#lp-email'), ACCOUNT.email)
  await typeInto(page, page.locator('#lp-pass'), ACCOUNT.password)
  await clickAt(page, page.getByRole('button', { name: 'Zaloguj się', exact: true }).first(), { x: 0, y: 0 }, 2200)
  await page.getByRole('heading', { name: /Gdzie jest Twoje pole/i }).first().waitFor({ timeout: 20000 })
  await page.waitForTimeout(settleMs)
}

/** Zapisuje stan sesji (token w localStorage), żeby kolejne ujęcia nie logowały się od nowa. */
export async function saveStorage(context, file) {
  await context.storageState({ path: file })
}

/**
 * Stan zalogowania do wielokrotnego użytku. Logujemy się w przeglądarce tym samym
 * zapytaniem, którego używa aplikacja, i zapisujemy token w localStorage. Dzięki
 * temu ujęcia inne niż samo logowanie startują od razu na kroku 1.
 */
export async function ensureLoginState(browser, file) {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const page = await context.newPage()
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' })
  const ok = await page.evaluate(async (account) => {
    const r = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(account),
    })
    if (!r.ok) return false
    const body = await r.json()
    localStorage.setItem('wodnik_token', body.token)
    return true
  }, ACCOUNT)
  await context.storageState({ path: file })
  await context.close()
  return ok
}
