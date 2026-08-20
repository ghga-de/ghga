/**
 * Playwright test for user manager.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expectPageRequiresLogin } from '../utils/expect-login-required-error';
import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'User Manager',
  adminMenuItemUrl: '/user-manager',
});

test('does not show user manager when not logged in', async ({
  loggedOutAdminPage: page,
}) => {
  await expectPageRequiresLogin(page, 'User Management');
});

test('can use user manager when logged in', async ({ adminPage: page }) => {
  await expectTitle(page, 'User Manager');

  const main = page.locator('main');

  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('User Management');

  const table = main.getByRole('table');
  await expect(table.getByRole('cell', { name: 'Dr. John Doe' })).toBeVisible();
  await expect(table.getByRole('cell', { name: 'Fred Flintstone' })).toBeVisible();
  await expect(table).not.toContainText('No users found');
});
