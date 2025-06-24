/**
 * Playwright test for account page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from './fixtures';

test('does not show account page when not logged in', async ({ page }) => {
  const logIn = page.getByRole('button', { name: 'Log In' });
  await expect(logIn).toHaveCount(0);

  await page.goto('/account');
  await expect(page).toHaveTitle('Home | GHGA Data Portal');

  const main = page.locator('main');
  await expect(main).not.toContainText('Account');
});

test('show account page when logged in', async ({ loggedInPage }) => {
  const page = loggedInPage;
  await expect(page).toHaveTitle('Home | GHGA Data Portal');

  const accountMenu = page.getByRole('button', { name: 'Account' });
  await expect(accountMenu).toBeVisible();
  await accountMenu.click();
  const accountItem = page.getByRole('menuitem', { name: 'Your GHGA account page' });
  await expect(accountItem).toBeVisible();
  await accountItem.click();

  await expect(page).toHaveTitle('User Account | GHGA Data Portal');
  await expect(page).toHaveURL('/account');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('User Account');
  const subHeading = main.getByRole('heading', { level: 2 });
  await expect(subHeading).toContainText('Dr. John Doe');

  // add more tests after adding arial labels

  await expect(main).toContainText('Email');
  await expect(main).toContainText(
    'We will communicate with you via this email address: doe@home.org',
  );

  await expect(main).toContainText('Contact addresses for account verification');
  await expect(main).toContainText('SMS: +441234567890004');

  await expect(main).toContainText('Dataset Access');
  await expect(main).toContainText(
    /For the dataset GHGAD12345678901235 from .* to .* – .* days left\./,
  );

  await expect(main).toContainText('Pending Access Requests');
  await expect(main).toContainText(
    /For the dataset GHGAD12345678901235 from .* to .*\./,
  );
});
