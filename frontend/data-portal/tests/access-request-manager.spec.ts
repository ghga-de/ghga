/**
 * Playwright test for access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from './fixtures';
import { expectTitle } from './utils/expect-title';

test('does not show access request manager when not logged in', async ({ page }) => {
  const logIn = page.getByRole('button', { name: 'Log In' });
  await expect(logIn).toHaveCount(0);

  const adminMenu = page.getByRole('navigation').getByLabel('Administration');
  await expect(adminMenu).toHaveCount(0);

  await page.goto('/iva-manager');
  await expectTitle(page, 'Home');

  const main = page.locator('main');
  await expect(main).not.toContainText('Request Management');
});

test('can use access request manager when logged in', async ({ loggedInPage }) => {
  const page = loggedInPage;
  await expectTitle(page, 'Home');

  const adminMenu = page.getByRole('navigation').getByLabel('Administration');
  await adminMenu.click();

  const managerItem = page.getByRole('menuitem', { name: 'Access Request Manager' });
  await expect(managerItem).toBeVisible();
  await managerItem.click();

  await expectTitle(page, 'Access Request Manager');
  await expect(page).toHaveURL('/access-request-manager');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Access Request Management');

  // add tests for the functionality of the access request manager
});
