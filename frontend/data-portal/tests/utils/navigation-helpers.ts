/**
 * Playwright navigation helper utilities.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, Locator, Page } from '@playwright/test';

/**
 * Perform a resilient click for flaky cross-browser actionability cases.
 * @param target the locator to click
 * @param options optional timing configuration
 * @param options.timeout timeout in ms for the regular click
 * @param options.fallbackTimeout timeout in ms for the fallback forced click
 * @returns no value
 */
export async function clickWithFallback(
  target: Locator,
  options: {
    timeout?: number;
    fallbackTimeout?: number;
  } = {},
): Promise<void> {
  const timeout = options.timeout ?? 7000;
  const fallbackTimeout = options.fallbackTimeout ?? 5000;

  try {
    await target.click({ timeout });
  } catch {
    await target.click({ force: true, timeout: fallbackTimeout });
  }
}

/**
 * Retry a click action until navigation reaches the expected URL.
 * @param page the Playwright page instance
 * @param clickTarget the locator to click for navigation
 * @param url the expected destination URL matcher
 * @param options optional retry/timing configuration
 * @param options.attempts number of click attempts before final assertion
 * @param options.clickTimeout timeout in ms for each regular click attempt
 * @param options.clickFallbackTimeout timeout in ms for each forced-click fallback
 * @param options.perAttemptTimeout timeout in ms for each waitForURL attempt
 * @param options.finalTimeout timeout in ms for the final toHaveURL assertion
 * @returns no value
 */
export async function clickAndWaitForUrl(
  page: Page,
  clickTarget: Locator,
  url: string | RegExp | ((url: URL) => boolean),
  options: {
    attempts?: number;
    clickTimeout?: number;
    clickFallbackTimeout?: number;
    perAttemptTimeout?: number;
    finalTimeout?: number;
  } = {},
): Promise<void> {
  const attempts = options.attempts ?? 2;
  const clickTimeout = options.clickTimeout ?? 5000;
  const clickFallbackTimeout = options.clickFallbackTimeout ?? 3000;
  const perAttemptTimeout = options.perAttemptTimeout ?? 7000;
  const finalTimeout = options.finalTimeout ?? 15000;

  for (let attempt = 0; attempt < attempts; attempt += 1) {
    await clickWithFallback(clickTarget, {
      timeout: clickTimeout,
      fallbackTimeout: clickFallbackTimeout,
    });
    const reachedTarget = await page
      .waitForURL(url, { timeout: perAttemptTimeout })
      .then(() => true)
      .catch(() => false);
    if (reachedTarget) {
      break;
    }
  }

  await expect(page).toHaveURL(url, { timeout: finalTimeout });
}
