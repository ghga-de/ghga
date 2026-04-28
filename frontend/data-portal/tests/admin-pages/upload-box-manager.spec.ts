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

test('validates required fields in the create upload box dialog', async ({
  adminPage: page,
}) => {
  const createButton = page.getByRole('button', { name: 'Create Upload Box' });
  await expect(createButton).toBeVisible();
  await createButton.click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Creeate a new Upload Box');

  const okButton = dialog.getByRole('button', { name: 'OK' });
  await expect(okButton).toBeDisabled();

  await dialog.getByLabel('Title').fill('   ');
  await dialog.getByLabel('Description').fill('   ');
  await expect(okButton).toBeDisabled();

  await dialog.getByLabel('Title').fill('Playwright Upload Box Validation');
  await dialog.getByLabel('Description').fill('Dialog validation test description');
  await expect(okButton).toBeDisabled();

  await dialog.getByRole('combobox', { name: 'Storage location' }).click();
  await page.getByRole('option', { name: 'Tübingen 1' }).click();

  await expect(okButton).toBeEnabled();

  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await expect(dialog).toHaveCount(0);
});

test('can create an upload box from the manager page', async ({ adminPage: page }) => {
  const title = 'Playwright Created Upload Box';
  const createButton = page.getByRole('button', { name: 'Create Upload Box' });
  await expect(createButton).toBeVisible();
  await createButton.click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toBeVisible();

  await dialog.getByLabel('Title').fill(title);
  await dialog.getByLabel('Description').fill('Created via E2E coverage test');
  await dialog.getByRole('combobox', { name: 'Storage location' }).click();
  await page.getByRole('option', { name: 'Heidelberg 2' }).click();
  await dialog.getByRole('button', { name: 'OK' }).click();

  const notification = page.locator('app-custom-snack-bar');
  await expect(notification).toContainText(/upload box created successfully/i);

  const main = page.locator('main');
  await expect(main.getByText(title)).toBeVisible();
});
