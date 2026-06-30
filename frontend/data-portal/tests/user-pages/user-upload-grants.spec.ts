/**
 * Playwright tests for user upload grants workflows on the account page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page } from '@playwright/test';
import { expect, test } from '../shared-features/fixtures';
import { expectTitle } from '../utils/expect-title';

/**
 * Navigate to the account page through the account menu.
 * @param page - the Playwright page
 */
async function goToAccountPage(page: Page) {
  await expectTitle(page, 'Home');

  const accountMenu = page.getByRole('button', { name: 'Account' });
  await expect(accountMenu).toBeVisible();
  await accountMenu.click();

  const accountItem = page.getByRole('menuitem', { name: 'Your GHGA account page' });
  await expect(accountItem).toBeVisible();
  await accountItem.click();

  await expect(page).toHaveURL('/account');
  await expectTitle(page, 'User Account');
}

test('shows the Research Data Upload section with user upload grants', async ({
  loggedInPage: page,
}) => {
  await goToAccountPage(page);

  const main = page.locator('main');
  await expect(
    main.getByRole('heading', { level: 2, name: 'Research Data Upload' }),
  ).toBeVisible();
  await expect(main).toContainText(
    'The following open Research Data Upload Boxes are assigned to you:',
  );

  await expect(main.getByText('Research Data Upload Box of John')).toBeVisible();
  await expect(
    main
      .getByRole('button', { name: 'Create an upload token for this upload box' })
      .first(),
  ).toBeVisible();
  await expect(
    main.getByRole('button', { name: 'Submit this upload box as complete' }).first(),
  ).toBeVisible();
});

test('can open and close the upload token dialog from the account upload section', async ({
  loggedInPage: page,
}) => {
  await goToAccountPage(page);

  const createTokenButton = page
    .getByRole('button', { name: 'Create an upload token for this upload box' })
    .first();
  await expect(createTokenButton).toBeVisible();
  await createTokenButton.click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Create an Upload Token');
  await expect(dialog).toContainText('Research Data Upload Box of John');

  await dialog.getByRole('button', { name: 'Close' }).click();
  await expect(dialog).toHaveCount(0);
});

test('keeps the box when submission is cancelled and removes it when confirmed', async ({
  loggedInPage: page,
}) => {
  await goToAccountPage(page);

  const main = page.locator('main');
  const rowTitle = 'Research Data Upload Box of John';
  const submitButton = main
    .getByRole('button', { name: 'Submit this upload box as complete' })
    .first();

  await expect(main.getByText(rowTitle)).toBeVisible();

  await submitButton.click();
  const firstDialog = page.getByRole('dialog');
  await expect(firstDialog).toContainText('Submit upload box?');
  await firstDialog.getByRole('button', { name: 'Cancel' }).click();

  await expect(main.getByText(rowTitle)).toBeVisible();

  await submitButton.click();
  const secondDialog = page.getByRole('dialog');
  await expect(secondDialog).toContainText('Submit upload box?');
  await secondDialog.getByRole('button', { name: 'Submit' }).click();

  const notification = page.locator('app-custom-snack-bar');
  await expect(notification).toContainText(/submitted successfully/i);
  await expect(main.getByText(rowTitle)).toHaveCount(0);
});
