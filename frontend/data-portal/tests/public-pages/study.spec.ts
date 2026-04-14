/**
 * Playwright test for study landing page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from '@playwright/test';

test('can show the study details page', async ({ page }) => {
  await page.goto('/study/GHGAS12345678901234');

  const h1 = page.getByRole('heading', { level: 1 }).getByText('Study Details');
  await expect(h1).toBeVisible();

  const egaLink = page.getByRole('link', { name: 'Visit EGA Study Page (new tab)' });
  await expect(egaLink).toBeVisible();
  await expect(egaLink).toHaveAttribute(
    'href',
    'https://ega-archive.org/studies/EGAS12345678901',
  );

  const download = page.getByRole('link', { name: 'Download Metadata' });
  await expect(download).toBeVisible();

  const h2 = page.getByRole('heading', { level: 2 }).getByText('Test Study');
  await expect(h2).toBeVisible();

  const h3 = page.getByRole('heading', { level: 3 }).getByText('Datasets');
  await expect(h3).toBeVisible();

  const dsLink = page.getByRole('link', { name: 'GHGAD12345678901235' });
  await expect(dsLink).toBeVisible();
});
