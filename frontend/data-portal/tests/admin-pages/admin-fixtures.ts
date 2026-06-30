/**
 * Playwright fixtures for admin page tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page } from '@playwright/test';
import { test as baseTest, expect } from '../shared-features/fixtures';

type AdminFixtures = {
  /** The name of the menu item in the Administration menu to navigate to. */
  adminMenuItemName: string;
  /** The url of the menu item in the Administration menu to navigate to. */
  adminMenuItemUrl: string;
  /** A page already navigated to the admin section selected via adminMenuItemName. */
  adminPage: Page;
  /** A page already navigated to the admin section URL while logged out. */
  loggedOutAdminPage: Page;
};

export const test = baseTest.extend<AdminFixtures>({
  adminMenuItemName: ['', { option: true }],
  adminMenuItemUrl: ['', { option: true }],
  /**
   * Create a new page already navigated to the selected admin section
   * @param opts the options
   * @param opts.loggedInPage the already logged-in page
   * @param opts.adminMenuItemName the menu item name to click
   * @param opts.adminMenuItemUrl the expected URL after navigation
   * @param use the use function of Playwright
   */
  adminPage: async ({ loggedInPage, adminMenuItemName, adminMenuItemUrl }, use) => {
    if (!adminMenuItemName) {
      throw new Error(
        'adminPage fixture requires adminMenuItemName to be set to a non-empty string.',
      );
    }
    if (!adminMenuItemUrl) {
      throw new Error(
        'adminPage fixture requires adminMenuItemUrl to be set to a non-empty string.',
      );
    }
    const page = loggedInPage;
    const adminMenuTrigger = page.getByRole('button', {
      name: 'Administration menu',
      exact: true,
    });
    const managerItem = page.getByRole('menuitem', {
      name: adminMenuItemName,
      exact: true,
    });

    await expect(adminMenuTrigger).toBeVisible();
    for (let attempt = 0; attempt < 3; attempt += 1) {
      await adminMenuTrigger.click();
      if (await managerItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        break;
      }
    }

    await expect(managerItem).toBeVisible({ timeout: 10000 });
    await managerItem.click();
    await page.waitForURL(
      (url) => url.pathname.replace(/\/?$/, '') === adminMenuItemUrl,
    );
    await use(page);
  },
  /**
   * Create a page in logged-out state and navigate to the selected admin route.
   * @param opts the options
   * @param opts.page the test page
   * @param opts.adminMenuItemUrl the target admin URL
   * @param use the use function of Playwright
   */
  loggedOutAdminPage: async ({ page, adminMenuItemUrl }, use) => {
    if (!adminMenuItemUrl) {
      throw new Error(
        'loggedOutAdminPage fixture requires adminMenuItemUrl to be set to a non-empty string.',
      );
    }

    await page.goto(adminMenuItemUrl);
    await use(page);
  },
});

export { expect } from '../shared-features/fixtures';
