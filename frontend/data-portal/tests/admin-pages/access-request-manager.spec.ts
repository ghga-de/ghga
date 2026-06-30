/**
 * Playwright test for access request manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expectPageRequiresLogin } from '../utils/expect-login-required-error';
import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'Access Request Manager',
  adminMenuItemUrl: '/access-request-manager',
});

test('does not show access request manager when not logged in', async ({
  loggedOutAdminPage: page,
}) => {
  await expectPageRequiresLogin(page, 'Request Management');
});

test('can use access request manager when logged in', async ({ adminPage: page }) => {
  await expectTitle(page, 'Access Request Manager');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Access Request Management');

  // add tests for the functionality of the access request manager
});
