/**
 * Playwright test for dataset browsing.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from '@playwright/test';
import { expectTitle } from '../utils/expect-title';
import { clickAndWaitForUrl } from '../utils/navigation-helpers';

test('can browse data', async ({ page }) => {
  await page.goto('/');

  const headerNavigation = page.getByRole('navigation', {
    name: 'Header Navigation',
  });
  const browseDataLink = headerNavigation.getByRole('link', {
    name: 'Browse Data',
    exact: true,
  });

  await expect(browseDataLink).toBeVisible();
  await clickAndWaitForUrl(page, browseDataLink, '/browse', {
    perAttemptTimeout: 5000,
    finalTimeout: 10000,
  });

  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets:26');
  await expect(main).toContainText('GHGAD12345678901236');
  await expect(main).toContainText('Test dataset for details');
});

test('can view a dataset summary', async ({ page }) => {
  await page.goto('/browse');

  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets:26', { timeout: 15000 });

  await expect(main).toContainText('GHGAD12345678901236');
  await expect(main).toContainText('Test dataset for details');

  // description and dataset summary are not yet visible
  await expect(main).not.toContainText('This is the test dataset description');
  await expect(main).not.toContainText('14 Experiments');

  const openSummary = page.getByRole('button', { name: 'GHGAD12345678901236' });
  await expect(openSummary).toBeVisible();
  await openSummary.click();

  // now the description and summary should be visible
  await expect(main).toContainText('This is the test dataset description');
  await expect(main).toContainText('14 Experiments');
});

test('can navigate to dataset details', async ({ page }) => {
  await page.goto('/browse');
  const main = page.locator('main');
  await expect(main).toContainText('Total Datasets:26', { timeout: 15000 });
  await expect(main).toContainText('GHGAD12345678901236');

  const resultPanel = main
    .locator('mat-expansion-panel')
    .filter({ hasText: 'GHGAD12345678901236' })
    .first();

  const openSummary = resultPanel.getByRole('button', {
    name: 'GHGAD12345678901236',
  });
  await expect(openSummary).toBeVisible();
  await openSummary.click();

  await expect(page).toHaveURL('/browse');

  const datasetDetailsLink = resultPanel.getByRole('link', {
    name: 'Dataset Details',
    exact: true,
  });
  await expect(datasetDetailsLink).toBeVisible();
  await datasetDetailsLink.click();

  await expect(page).toHaveURL('/dataset/GHGAD12345678901236');

  await expectTitle(page, 'Dataset GHGAD12345678901236');

  await expect(main).toContainText('Dataset ID | GHGAD12345678901236');
  await expect(main).toContainText('Test dataset with some details for testing.');

  await expect(main).toContainText('Test study description.');
  await expect(main).toContainText('List of files (12 total, 6.16 GiB)');

  // files table should not yet be visible
  await expect(main).not.toContainText('File ID');
  await expect(main).not.toContainText('GHGAF12345678901243');
  await expect(main).not.toContainText('Research data file 3');
  await expect(main).not.toContainText('Tübingen 3');

  const openFile = main.getByRole('button', { name: 'List of files' });
  await expect(openFile).toBeVisible();
  await openFile.click();

  // files table should now be visible
  await expect(main).toContainText('File ID');
  await expect(main).toContainText('GHGAF12345678901243');
  await expect(main).toContainText('Research data file 3');
  await expect(main).toContainText('Tübingen 3');

  // last file should bot yet be visible
  await expect(main).not.toContainText('GHGAF12345678901245');
  await expect(main).not.toContainText('Research data file 5');

  const nextPageButton = main.getByRole('button', { name: 'Next page' });
  await expect(nextPageButton).toBeVisible();
  await nextPageButton.click();

  // last file should now be visible
  await expect(main).toContainText('GHGAF12345678901245');
  await expect(main).toContainText('Research data file 5');
});
