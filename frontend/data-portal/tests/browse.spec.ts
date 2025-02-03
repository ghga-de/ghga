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
  await expect(main).toContainText('Total Datasets: 25');
  await expect(main).toContainText('GHGAD588887989');
  await expect(main).toContainText('Test dataset for details');
});

test('can view a dataset summary', async ({ page }) => {
  await page.goto('/browse');

  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets: 25');

  await expect(main).toContainText('GHGAD588887989');
  await expect(main).toContainText('Test dataset for details');

  await expect(
    page.getByText('Description: This is the test dataset description'),
  ).not.toBeVisible();

  const openSummaryLink = page.getByText('GHGAD588887989');
  await expect(openSummaryLink).toBeVisible();
  await openSummaryLink.click();

  await expect(
    page.getByText('Description: This is the test dataset description'),
  ).toBeVisible();
});

test('can navigate to dataset details', async ({ page }) => {
  await page.goto('/browse');

  await page.getByText('GHGAD588887989').click();

  await expect(page).toHaveURL('/browse');

  await page.getByText('Dataset Details').click();

  await expect(page).toHaveURL('/dataset/GHGAD588887989');

  await expect(page).toHaveTitle('Dataset GHGAD588887989 | GHGA Data Portal');

  await expect(page.getByText('Dataset ID | GHGAD588887989')).toBeVisible();

  await expect(
    page.getByText('Test dataset with some details for testing.'),
  ).toBeVisible();
});
