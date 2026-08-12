/**
 * Shared HTTP cache settings
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpContext } from '@angular/common/http';
import { CacheBucket, withCache } from '@ngneat/cashew';

/**
 * How long a response may be reused for data that goes stale on its own.
 *
 * Most cached responses in this application are metadata that changes only with
 * an archive release, and they keep the long global time to live configured in
 * `app.config.ts`. Upload boxes, grants, access requests and the like are
 * different: they are changed by other users, and files are uploaded with the
 * GHGA Connector entirely outside the portal. The services drop the affected
 * cache entries themselves whenever they change data or fetch it again, so this
 * is only a backstop for an invalidation that was overlooked — short enough to
 * heal on its own, long enough to still collapse a burst of identical requests.
 */
export const VOLATILE_CACHE_TTL = 60_000;

/**
 * Build the request context for an endpoint whose data changes on its own.
 * @param bucket - collects the cache keys of this endpoint, so that all of its
 *   variants (pages, sort orders, filters) can be invalidated together
 * @returns the HTTP context to pass along with the request
 */
export function volatileCacheContext(bucket: CacheBucket): HttpContext {
  return withCache({ bucket, ttl: VOLATILE_CACHE_TTL });
}
