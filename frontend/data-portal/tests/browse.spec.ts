/**
 * Playwright test for dataset browsing.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from '@playwright/test';

test('can browse data', async ({ page }) => {
  await page.goto('/');

  const browseDataLink = page.getByText('Browse Data').first();
  await expect(browseDataLink).toBeVisible();
  await browseDataLink.click();

  await expect(page).toHaveURL('/browse');

  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets:25');
  await expect(main).toContainText('GHGAD588887989');
  await expect(main).toContainText('Test dataset for details');
});

test('can view a dataset summary', async ({ page }) => {
  await page.goto('/browse');

  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets:25');

  await expect(main).toContainText('GHGAD588887989');
  await expect(main).toContainText('Test dataset for details');

  // description is not yet visible
  await expect(main).not.toContainText('This is the test dataset description');

  const openSummaryLink = page.getByText('GHGAD588887989');
  await expect(openSummaryLink).toBeVisible();
  await openSummaryLink.click();

  await expect(main).toContainText('This is the test dataset description');
});

test('can navigate to dataset details', async ({ page }) => {
  await page.goto('/browse');
  const main = page.locator('main');

  await main.getByText('GHGAD588887989').click();

  await expect(page).toHaveURL('/browse');

  const button = page.getByLabel('GHGAD588887989').getByText('Dataset Details');
  await expect(button).toBeVisible();
  await button.click();

  await expect(page).toHaveURL('/dataset/GHGAD588887989');

  await expect(page).toHaveTitle('Dataset GHGAD588887989 | GHGA Data Portal');

  await expect(main).toContainText('Dataset ID | GHGAD588887989');

  await expect(main).toContainText('Test dataset with some details for testing.');
});
