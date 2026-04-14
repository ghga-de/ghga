/**
 * Playwright test for IVA manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expectPageRequiresLogin } from '../utils/expect-login-required-error';
import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'IVA Manager',
  adminMenuItemUrl: '/iva-manager',
});

test('does not show IVA manager when not logged in', async ({
  loggedOutAdminPage: page,
}) => {
  await expectPageRequiresLogin(page, 'Address Management');
});

test('can use IVA manager when logged in', async ({ adminPage: page }) => {
  await expectTitle(page, 'IVA Manager');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Independent Verification Address Management');

  // add tests for the functionality of the IVA manager
});
