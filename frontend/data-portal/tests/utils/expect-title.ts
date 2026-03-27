/**
 * Utility function to check page title
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page, expect } from '@playwright/test';

/**
 * A helper to check the page title
 * @param page the page to check
 * @param titlePrefix the title prefix to expect (the full title is expected to be `${titlePrefix} | GHGA Data Portal`)
 */
export async function expectTitle(page: Page, titlePrefix: string) {
  await expect(page).toHaveTitle(`${titlePrefix} | GHGA Data Portal`);
}
