/**
 * In many places, we need a mock for the Activated Route. This is a very basic implementation to be re-used.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ActivatedRoute } from '@angular/router';

export const fakeActivatedRoute = {
  snapshot: { data: {} },
} as ActivatedRoute;
