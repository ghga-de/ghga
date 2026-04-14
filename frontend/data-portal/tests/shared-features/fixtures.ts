/**
 * Playwright fixtures
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { test as baseTest, expect, Page } from '@playwright/test';

type SharedFixtures = {
  loggedInPage: Page;
};

export const test = baseTest.extend<SharedFixtures>({
  /**
   * Create a new page where the user is already logged in.
   * @param opts the options
   * @param opts.context the browser context to use
   * @param use the use function of Playwright
   */
  loggedInPage: async ({ context }, use) => {
    const page = await context.newPage();
    await page.goto('/');
    const logIn = page.getByRole('button', { name: 'Log in' });
    await expect(logIn).toBeVisible();
    await logIn.click();
    const lsLogin = page.getByRole('menuitem', { name: 'LS Login' });
    await expect(lsLogin).toBeVisible();
    await lsLogin.click();
    await use(page);
    const account = page.getByRole('button', { name: 'Account' });
    await expect(account).toBeVisible();
  },
});

export { expect } from '@playwright/test';
