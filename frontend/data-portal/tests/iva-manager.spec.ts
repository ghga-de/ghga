/**
 * Playwright test for IVA manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from './fixtures';
import { expectTitle } from './utils/expect-title';

test('does not show IVA manager when not logged in', async ({ page }) => {
  const logIn = page.getByRole('button', { name: 'Log In' });
  await expect(logIn).toHaveCount(0);

  const adminMenu = page.getByRole('navigation').getByLabel('Administration');
  await expect(adminMenu).toHaveCount(0);

  await page.goto('/iva-manager');
  await expectTitle(page, 'Home');

  const main = page.locator('main');
  await expect(main).not.toContainText('Address Management');
});

test('can use IVA manager when logged in', async ({ loggedInPage }) => {
  const page = loggedInPage;
  await expectTitle(page, 'Home');

  const adminMenu = page.getByRole('navigation').getByLabel('Administration');
  await adminMenu.click();

  const managerItem = page.getByRole('menuitem', { name: 'IVA Manager' });
  await expect(managerItem).toBeVisible();
  await managerItem.click();

  await expectTitle(page, 'IVA Manager');
  await expect(page).toHaveURL('/iva-manager');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Independent Verification Address Management');

  // add tests for the functionality of the IVA manager
});
