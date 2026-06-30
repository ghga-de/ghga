/**
 * Utility function to check page title
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page, expect } from '@playwright/test';

/**
 * A helper to check the page title
 * @param page the page to check
 * @param titlePrefix the title prefix to expect
 */
export async function expectTitle(page: Page, titlePrefix: string) {
  await expect(page).toHaveTitle(
    !titlePrefix || titlePrefix === 'Home'
      ? /^(?:Home \| )?GHGA Data Portal$/
      : `${titlePrefix} | GHGA Data Portal`,
  );
}
