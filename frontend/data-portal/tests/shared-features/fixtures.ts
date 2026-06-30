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
    const account = page.getByRole('button', { name: 'Account' });

    // Reuse existing authenticated state if present in this browser context.
    if (!(await account.isVisible({ timeout: 1000 }).catch(() => false))) {
      const logIn = page.getByRole('button', { name: 'Log in', exact: true });
      const lsLoginByRole = page.getByRole('button', { name: /ls login/i });
      const lsLoginByMenuItem = page.getByRole('menuitem', { name: /ls login/i });
      const lsLoginByImage = page
        .locator('button')
        .filter({ has: page.getByAltText('LS Login') })
        .first();

      let lsLoginVisible = false;
      for (let attempt = 0; attempt < 3; attempt += 1) {
        await expect(logIn).toBeVisible({ timeout: 10000 });
        await logIn.click();

        lsLoginVisible =
          (await lsLoginByRole.isVisible({ timeout: 2000 }).catch(() => false)) ||
          (await lsLoginByMenuItem.isVisible({ timeout: 2000 }).catch(() => false)) ||
          (await lsLoginByImage.isVisible({ timeout: 2000 }).catch(() => false));
        if (lsLoginVisible) break;
      }

      const hasLsLoginButton = await lsLoginByRole
        .isVisible({ timeout: 1000 })
        .catch(() => false);
      const hasLsLoginMenuItem = await lsLoginByMenuItem
        .isVisible({ timeout: 1000 })
        .catch(() => false);

      const lsLogin = hasLsLoginButton
        ? lsLoginByRole.first()
        : hasLsLoginMenuItem
          ? lsLoginByMenuItem.first()
          : lsLoginByImage;
      await expect(lsLogin).toBeVisible({ timeout: 10000 });

      try {
        await lsLogin.click({ timeout: 10000 });
      } catch {
        // WebKit can occasionally stall while clicking the menuitem itself.
        // Clicking the contained LS Login image triggers the same action.
        await page.getByAltText('LS Login').first().click({ timeout: 5000 });
      }

      // The mock OIDC flow briefly navigates to the current page with callback-like
      // query parameters before cleaning them up again.
      await page.waitForURL(
        (url) =>
          !url.searchParams.has('client_id') && !url.searchParams.has('redirect_uri'),
        { timeout: 15000 },
      );
    }

    await expect(account).toBeVisible({ timeout: 15000 });
    await use(page);
  },
});

export { expect } from '@playwright/test';
