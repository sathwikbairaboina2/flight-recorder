import { expect, test } from '@playwright/test'

const shots = process.env.FR_SCREENSHOTS === '1'
const shot = async (page: import('@playwright/test').Page, name: string) => {
  if (shots) await page.screenshot({ path: `../docs/img/${name}.png` })
}

test('find the dropped date filter and fix it with a fork', async ({ page }) => {
  await page.goto('/?thread=lisbon-bug')
  const rows = page.getByTestId('timeline-row')
  await expect(rows).toHaveCount(5)
  await expect(page.getByTestId('inspector')).toContainText('TP1351') // the wrong, October answer

  // step back to the checkpoint written by the plan node
  await page.keyboard.press('k')
  await page.keyboard.press('k') // rows: input, __start__, plan, tools, answer
  await expect(page.getByTestId('inspector')).toContainText('search_flights')
  await expect(page.getByTestId('timeline-row').nth(2)).toHaveAttribute('aria-selected', 'true')
  await shot(page, '01-timeline')

  await page.keyboard.press('d')
  await expect(page.getByTestId('diff-panel')).toContainText('messages')
  await shot(page, '02-diff')

  await page.keyboard.press('f')
  const box = page.getByLabel('Fork values')
  const text = await box.inputValue()
  await box.fill(text.replace('"depart_after": null', '"depart_after": "2026-11-01"'))
  await expect(page.getByLabel('As node')).toHaveValue('plan')
  await page.getByRole('button', { name: 'Run fork' }).click()
  await expect(page.getByTestId('fork-result')).toContainText('done')
  await page.getByRole('button', { name: 'Open fork' }).click()

  await expect(rows).toHaveCount(6)
  await expect(page.getByTestId('inspector')).toContainText('TP1363') // the right, November answer
  await expect(page.locator('[data-origin="scratch"]').first()).toBeVisible()
  await shot(page, '03-fork')
})

test('the source thread is unchanged after the fork', async ({ page }) => {
  await page.goto('/?thread=lisbon-bug')
  await expect(page.getByTestId('timeline-row')).toHaveCount(5)
  await expect(page.getByTestId('inspector')).toContainText('TP1351')
})
