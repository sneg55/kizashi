import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import { chromium } from 'playwright'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const BASE = process.env.KIZASHI_UI || 'https://kizashi.nsawinyh.workers.dev'
const OUT = path.join(__dirname, 'out', 'inspect')
fs.mkdirSync(OUT, { recursive: true })

async function dump(page, label) {
  const info = await page.evaluate(() => {
    const pick = (el) => ({
      tag: el.tagName.toLowerCase(),
      testid: el.getAttribute('data-testid') || undefined,
      id: el.id || undefined,
      cls: (el.getAttribute('class') || '').slice(0, 90) || undefined,
      aria: el.getAttribute('aria-expanded') || undefined,
      ctl: el.getAttribute('aria-controls') || undefined,
      role: el.getAttribute('role') || undefined,
      ph: el.getAttribute('placeholder') || undefined,
      text: (el.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 80) || undefined,
    })
    const sections = [...document.querySelectorAll('section,[id]')]
      .map((e) => ({ tag: e.tagName.toLowerCase(), id: e.id || undefined, cls: (e.getAttribute('class') || '').slice(0, 70) || undefined, h: (e.querySelector('h1,h2,h3')?.innerText || '').trim().slice(0, 60) || undefined }))
      .filter((e) => e.id || e.h)
    return {
      title: document.title,
      h1: [...document.querySelectorAll('h1,h2,h3')].map((e) => e.innerText.trim().replace(/\s+/g, ' ').slice(0, 80)),
      buttons: [...document.querySelectorAll('button')].map(pick).slice(0, 70),
      inputs: [...document.querySelectorAll('input,textarea,select')].map(pick),
      sections,
      scrollH: document.body.scrollHeight,
    }
  })
  console.log(`\n===== ${label} =====`)
  console.log(JSON.stringify(info, null, 1))
  await page.screenshot({ path: path.join(OUT, `${label}.png`) })
  await page.screenshot({ path: path.join(OUT, `${label}-full.png`), fullPage: true })
  return info
}

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
try {
  await page.goto(BASE, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  await dump(page, '01-landing')

  await page.goto(`${BASE}/app`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(3000)
  await dump(page, '02-app')

  const text = await page.evaluate(() => document.body.innerText.slice(0, 12000))
  fs.writeFileSync(path.join(OUT, 'app-text.txt'), text)
  console.log('\n===== APP TEXT (first 4000) =====\n' + text.slice(0, 4000))
} catch (e) {
  console.error('inspect error:', e.message)
  process.exitCode = 1
} finally {
  await browser.close()
}
