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

// TODO: adapt and activate this test when the metadata browser is implemented
test.skip('can navigate to dataset details', async ({ page }) => {
  await page.goto('/');

  // Open summary view
  await page.getByText('GHGAD00446744119764').click();

  // Open dataset details vie
  await page.getByText('View dataset details').click();

  // Expect to find the dataset ID
  await expect(page.getByText('Dataset ID: GHGAD00446744119764')).toBeVisible();

  // Expect to find the study title
  await expect(
    page.getByText(
      'Title: Comprehensive Genomic and Transcriptomic Analysis' +
        ' of Rare Cancers for Guiding of Therapy (H021)',
    ),
  ).toBeVisible();
});
