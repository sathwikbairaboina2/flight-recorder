import { mkdirSync, writeFileSync } from 'node:fs'
import os from 'node:os'
import { expect, test } from '@playwright/test'

const N = 10_000
const median = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  return Math.round(s[Math.floor(s.length / 2)] * 10) / 10
}
const p95 = (xs: number[]) => {
  const s = [...xs].sort((a, b) => a - b)
  return Math.round(s[Math.min(s.length - 1, Math.round(0.95 * (s.length - 1)))] * 10) / 10
}

test('open and scrub a 10,000-checkpoint thread', async ({ browser, browserName }) => {
  const opens: number[] = []
  for (let run = 0; run < 6; run++) {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(`/?thread=long-${N}`)
    await expect(page.getByTestId('timeline')).toHaveAttribute('data-count', String(N), { timeout: 60_000 })
    await expect(page.getByTestId('timeline-row').first()).toBeVisible()
    const ms = await page.evaluate(async () => {
      for (let i = 0; i < 200 && performance.getEntriesByName('fr:timeline-ready').length === 0; i++) {
        await new Promise((r) => setTimeout(r, 25))
      }
      return performance.getEntriesByName('fr:timeline-ready')[0]?.startTime ?? -1
    })
    expect(ms).toBeGreaterThan(0)
    opens.push(ms)
    await context.close()
  }

  const page = await browser.newPage()
  await page.goto(`/?thread=long-${N}`)
  await expect(page.getByTestId('timeline')).toHaveAttribute('data-count', String(N), { timeout: 60_000 })
  await expect(page.locator('[data-testid="inspector"][data-checkpoint-id]:not([data-checkpoint-id=""])')).toBeVisible({ timeout: 60_000 })
  // 50 presses of k from the newest row: every step lands on a checkpoint whose state is not cached yet
  const steps: number[] = await page.evaluate(async () => {
    const out: number[] = []
    // the inspector element is absent while a state is loading, so null means "not shown yet"
    const inspector = () => document.querySelector('[data-testid="inspector"]')?.getAttribute('data-checkpoint-id') ?? null
    const frame = () => new Promise((r) => requestAnimationFrame(() => r(null)))
    for (let i = 0; i < 50; i++) {
      const before = inspector()
      const t0 = performance.now()
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k' }))
      while (inspector() === null || inspector() === before) await frame()
      out.push(performance.now() - t0)
    }
    return out
  })
  const result = {
    machine: { platform: `${os.type()} ${os.release()}`, cpu: os.cpus()[0]?.model ?? 'unknown', browser: `${browserName} ${browser.version()}` },
    checkpoints: N,
    open_cold_ms: Math.round(opens[0] * 10) / 10,
    open_warm_median_ms: median(opens.slice(1)),
    open_runs: opens.map((x) => Math.round(x)),
    step_median_ms: median(steps),
    step_p95_ms: p95(steps),
    step_runs: steps.length,
  }
  mkdirSync('../bench/results', { recursive: true })
  writeFileSync('../bench/results/ui.json', JSON.stringify(result, null, 2) + '\n')
  console.log(result)
})
