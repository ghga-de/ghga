/**
 * Playwright test for Upload Box manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expectPageRequiresLogin } from '../utils/expect-login-required-error';
import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'Upload Box Manager',
  adminMenuItemUrl: '/upload-box-manager',
});

test('does not show Upload Box manager when not logged in', async ({
  loggedOutAdminPage: page,
}) => {
  await expectPageRequiresLogin(page, 'Upload Box Manager');
  const bar = page.locator('app-custom-snack-bar');
  await expect(bar).toContainText('Please login to continue');
});

test('can use Upload Box manager when logged in', async ({ adminPage: page }) => {
  await expectTitle(page, 'Upload Box Manager');

  const main = page.locator('main');
  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Upload Box Manager');

  // data list should be loaded
  const table = main.locator('table');
  await expect(table).toBeVisible();
  await expect(table.getByRole('columnheader', { name: 'Title' })).toBeVisible();
  await expect(table.getByRole('columnheader', { name: 'State' })).toBeVisible();
  const firstRow = table.locator('tbody tr').first();
  await expect(firstRow).toBeVisible();

  // Check for filter controls. On large viewports the filter panel is always visible (no toggle button),
  // while on small viewports a toggle button is used.
  const filterToggle = page.getByRole('button', { name: 'Filter upload boxes' });
  if (await filterToggle.isVisible()) {
    await filterToggle.click();
  }
  await expect(main.getByLabel('Upload box title').first()).toBeVisible();
  await expect(main.getByLabel('State').first()).toBeVisible();
  await expect(main.getByLabel('Location').first()).toBeVisible();
});

test('can navigate to Upload Box details', async ({ adminPage: page }) => {
  const detailsPageMain = page.locator('main');
  const detailsButton = detailsPageMain
    .getByRole('button', { name: 'View upload box details' })
    .first();
  await expect(detailsButton).toBeVisible();
  await detailsButton.click();
  await expect(page).toHaveURL(/\/upload-box-manager\/.+/);
  await expectTitle(page, 'Upload Box Details');

  const uploadBoxInfo = page.getByRole('heading', {
    level: 2,
    name: 'Upload Box Info',
  });
  await expect(uploadBoxInfo).toBeVisible();
  await expect(detailsPageMain).toContainText('Title:');
  await expect(detailsPageMain).toContainText('State:');
  await expect(detailsPageMain).toContainText('Description:');
  await expect(detailsPageMain).toContainText('Last change:');
  await expect(detailsPageMain).toContainText('Files / Size:');

  const uploadsGrantsCard = page.getByRole('heading', {
    level: 2,
    name: 'Upload Grants',
  });
  await expect(uploadsGrantsCard).toBeVisible();
  const storageCard = page.getByRole('heading', { level: 2, name: 'Storage & Files' });
  await expect(storageCard).toBeVisible();

  const backButton = page.getByRole('button', {
    name: 'Go back to previous page',
  });
  await expect(backButton).toBeVisible();
  await backButton.click();
  await expect(page).toHaveURL('/upload-box-manager');
});

test('can navigate to Add Grant page', async ({ adminPage: page }) => {
  const detailsButton = page
    .locator('main')
    .getByRole('button', { name: 'View upload box details' })
    .first();
  await detailsButton.click();
  await expect(page).toHaveURL(/\/upload-box-manager\/.+/);
  await expectTitle(page, 'Upload Box Details');

  const addGrantButton = page.getByRole('button', { name: 'Add new upload grant' });
  await expect(addGrantButton).toBeVisible();
  await addGrantButton.click();
  await expect(page).toHaveURL(/\/upload-box-manager\/.+\/grant\/new/);
  await expectTitle(page, 'New Upload Grant');

  const backButton = page.getByRole('button', {
    name: 'Go back to upload box details',
  });
  await expect(backButton).toBeVisible();
  await backButton.click();
  await expect(page).toHaveURL(/\/upload-box-manager\/.+/);
});

test('displays error message when upload box not found', async ({
  adminPage: page,
}) => {
  await page.goto('/upload-box-manager/invalid-id');

  const main = page.locator('main');
  await expect(main).toContainText('Upload box not found.');

  const backButton = page.getByRole('button', { name: 'Go back to previous page' });
  await expect(backButton).toBeVisible();
  await backButton.click();
  await expect(page).toHaveURL('/upload-box-manager');
});
