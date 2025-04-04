/**
 * Playwright fixtures
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { test as baseTest, expect, Page } from '@playwright/test';

type CustomFixtures = {
  loggedInPage: Page;
};

export const test = baseTest.extend<CustomFixtures>({
  /**
   * Create a new page where the user is already logged in.
   * @param opts the options
   * @param opts.browser the browser to use
   * @param use the use function of Playwright
   */
  loggedInPage: async ({ browser }, use) => {
    const page = await browser.newPage();
    await page.goto('/');
    const logIn = page.getByRole('button', { name: 'Log in' });
    await expect(logIn).toBeVisible();
    await logIn.click();
    const lsLogin = page.getByRole('menuitem', { name: 'LS Login' });
    await expect(lsLogin).toBeVisible();
    await lsLogin.click();
    use(page);
    const account = page.getByRole('button', { name: 'Account' });
    await expect(account).toBeVisible();
  },
});

export { expect } from '@playwright/test';
