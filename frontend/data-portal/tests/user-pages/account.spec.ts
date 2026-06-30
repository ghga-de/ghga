/**
 * Playwright test for account page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from '../shared-features/fixtures';
import { expectTitle } from '../utils/expect-title';

test('does not show account page when not logged in', async ({ page }) => {
  await page.goto('/');
  const logIn = page.getByRole('button', { name: 'Log in' });
  await expect(logIn).toBeVisible();

  await page.goto('/account');
  await expectTitle(page, 'Home');

  const main = page.locator('main');
  await expect(main).not.toContainText('Account');
});

test('show account page when logged in', async ({ loggedInPage }) => {
  const page = loggedInPage;
  await expectTitle(page, 'Home');

  const accountMenu = page.getByRole('button', { name: 'Account' });
  await expect(accountMenu).toBeVisible();
  await accountMenu.click();
  const accountItem = page.getByRole('menuitem', { name: 'Your GHGA account page' });
  await expect(accountItem).toBeVisible();
  await accountItem.click();

  await expectTitle(page, 'User Account');
  await expect(page).toHaveURL('/account');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('User Account');
  const subHeading = main.getByRole('heading', { level: 2 }).first();
  await expect(subHeading).toContainText('Dr. John Doe');

  // add more tests after adding arial labels

  await expect(main.getByRole('heading', { level: 2, name: 'Email' })).toBeVisible();
  await expect(main).toContainText(
    'We will communicate with you via this email address: doe@home.org',
  );

  await expect(
    main.getByRole('heading', {
      level: 2,
      name: 'Independent Verification Addresses (IVAs)',
    }),
  ).toBeVisible();
  await expect(main).toContainText('SMS: +441234567890004');

  await expect(
    main.getByRole('heading', { level: 2, name: 'Dataset Access' }),
  ).toBeVisible();
  await expect(main).toContainText(
    /For the dataset GHGAD12345678901235 from .* to .*\./,
  );

  await expect(
    main.getByRole('heading', { level: 2, name: 'Pending Access Requests' }),
  ).toBeVisible();
  await expect(main).toContainText(
    /For the dataset GHGAD12345678901235 from .* to .*\./,
  );
});
