import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'
import { FIRST_JOB_ID, installRoutes } from './fixtures'

const FIRST_TITLE = 'AI Engineer, Retrieval'

async function openWorkspace(
  page: Page,
  width: number,
  height: number,
  path: string,
) {
  await page.setViewportSize({ width, height })
  await page.goto(path)
  await expect(page.getByText('Asha Rao', { exact: true })).toBeVisible()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))
}

async function seriousViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze()
  return results.violations
    .filter(
      (violation) =>
        violation.impact === 'serious' || violation.impact === 'critical',
    )
    .map(
      (violation) =>
        `${violation.id} [${violation.nodes
          .map((node) => node.target.join(' '))
          .join(' | ')}]: ${violation.help}`,
    )
}

async function hasHorizontalOverflow(page: Page) {
  return page.evaluate(
    () =>
      document.documentElement.scrollWidth >
      document.documentElement.clientWidth,
  )
}

test.beforeEach(async ({ page }) => {
  await installRoutes(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
})

test('desktop dark and light states', async ({ page }) => {
  await openWorkspace(page, 1440, 1000, `/?resume=7&job=${FIRST_JOB_ID}`)
  await expect(
    page.getByRole('heading', { name: FIRST_TITLE }),
  ).toBeVisible()

  await page.screenshot({ path: 'screens/desktop-dark.png' })
  expect(await seriousViolations(page)).toEqual([])

  await page.getByRole('button', { name: 'Day theme' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light')
  await page.screenshot({ path: 'screens/desktop-light.png' })
  expect(await seriousViolations(page)).toEqual([])
})

test('tablet layout keeps the shortlist and case file', async ({ page }) => {
  await openWorkspace(page, 1024, 900, `/?resume=7&job=${FIRST_JOB_ID}`)

  await page.screenshot({ path: 'screens/tablet-dark.png' })
  expect(await hasHorizontalOverflow(page)).toBe(false)
})

test('mobile list and detail fit the screen', async ({ page }) => {
  await openWorkspace(page, 390, 844, '/?resume=7')

  expect(await hasHorizontalOverflow(page)).toBe(false)
  await page.screenshot({ path: 'screens/mobile-list-dark.png' })

  await page.getByRole('button', { name: new RegExp(FIRST_TITLE) }).click()
  await expect(
    page.getByRole('heading', { name: FIRST_TITLE }),
  ).toBeVisible()

  expect(await hasHorizontalOverflow(page)).toBe(false)
  await page.screenshot({ path: 'screens/mobile-detail-dark.png' })
})

test('upload state', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')
  await expect(
    page.getByRole('heading', { name: 'Open your candidate file' }),
  ).toBeVisible()
  await page.evaluate(() => document.fonts.ready.then(() => undefined))

  await page.screenshot({ path: 'screens/upload-dark.png' })
})
