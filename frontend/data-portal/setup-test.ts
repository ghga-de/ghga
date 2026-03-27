/**
 * Setup unit testing for Angular
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import '@testing-library/jest-dom/vitest';

if (typeof globalThis.IntersectionObserver === 'undefined') {
  /**
   * Provide a minimal test shim for Angular `@defer` (on viewport) in jsdom.
   */
  class IntersectionObserverMock implements IntersectionObserver {
    readonly root: Element | Document | null = null;
    readonly rootMargin = '';
    readonly thresholds: ReadonlyArray<number> = [];

    /** Disconnect: No-op in tests. */
    disconnect(): void {}

    /**
     * Observe: No-op in tests.
     * @param _target Ignored target element.
     */
    observe(_target: Element): void {}

    /**
     * TakeRecords: Returns no records in tests.
     * @returns Always an empty entry list.
     */
    takeRecords(): IntersectionObserverEntry[] {
      return [];
    }

    /**
     * Unobserve: No-op in tests.
     * @param _target Ignored target element.
     */
    unobserve(_target: Element): void {}
  }

  globalThis.IntersectionObserver = IntersectionObserverMock;
}
