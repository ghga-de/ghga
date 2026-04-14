/**
 * Utility helper for unauthorized-route checks.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page, expect } from '@playwright/test';
import { expectTitle } from './expect-title';

/**
 * A helper to check a logged-out user cannot access a protected route.
 * @param page a page already navigated to a protected route while logged out
 * @param pageTitle the title of the page that should not be visible to logged-out users
 * @returns no value
 */
export const expectPageRequiresLogin = async (page: Page, pageTitle: string) => {
  await expectTitle(page, 'Home');
  await expect(page).toHaveURL('/');
  const main = page.locator('main');
  await expect(main).not.toContainText(pageTitle);
};
