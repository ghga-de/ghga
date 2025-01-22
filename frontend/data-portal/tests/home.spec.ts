/**
 * Playwright test for the home page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from '@playwright/test';

test('has proper title', async ({ page }) => {
  await page.goto('/');

  await expect(page).toHaveTitle('Home | GHGA Data Portal');
});

test('has proper heading', async ({ page }) => {
  await page.goto('/');

  const heading = page.locator('h1');
  await expect(heading).toContainText('The German Human Genome-Phenome Archive');
  await expect(heading).toContainText('Data Portal');
});

test('has global statistics', async ({ page }) => {
  await page.goto('/');

  const main = page.locator('main');
  await expect(main).toContainText('Statistics');
  await expect(main).toContainText('Total datasets: 252');
  await expect(main).toContainText('Platforms: 1400');
  await expect(main).toContainText('Individuals: 5432');
  await expect(main).toContainText('Files: 532');
});
