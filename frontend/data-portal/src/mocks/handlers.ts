/**
 * Mock REST handlers
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { http, HttpResponse, RequestHandler } from 'msw';
import { handlers as authHandlers } from './auth';
import { responses as apiResponses, ResponseValue } from './responses';
import { umamiHandlers } from './umami';

const DELAY = 0; // delay in seconds for testing

/** A list response carrying its entries in an `items` array */
type Collection = { items: unknown[]; total_count?: number };

/**
 * Check whether a static response is a list response with an `items` array.
 * @param response - the static response to check
 * @returns whether the response is a collection
 */
function isCollection(response: ResponseValue): response is Collection {
  return (
    typeof response === 'object' &&
    response !== null &&
    Array.isArray((response as Collection).items)
  );
}

/**
 * Compare two entries of a collection by a single field.
 *
 * Entries without a value for the field sort last, numbers compare numerically
 * and everything else compares as a string.
 * @param left - the first entry
 * @param right - the second entry
 * @param field - the name of the field to compare by
 * @returns a negative number, zero, or a positive number for ordering
 */
function compareByField(left: unknown, right: unknown, field: string): number {
  const leftValue = (left as Record<string, unknown>)[field];
  const rightValue = (right as Record<string, unknown>)[field];
  if (leftValue == null || rightValue == null) {
    if (leftValue == rightValue) return 0;
    return leftValue == null ? 1 : -1;
  }
  if (typeof leftValue === 'number' && typeof rightValue === 'number') {
    return leftValue - rightValue;
  }
  return String(leftValue).localeCompare(String(rightValue));
}

/**
 * Derive the requested window of a complete collection response.
 *
 * This is the one piece of backend behaviour the mocks reproduce, because it is
 * a convention shared by all paginated list endpoints rather than logic specific
 * to any one of them: entries are sorted by the comma-separated field names in
 * `sort` (a leading dash denotes descending order), the total count is reported
 * before pagination, and `skip` and `limit` then select the page. Sorting has to
 * happen before slicing, which is why the mock cannot simply reorder a response
 * that is already a page.
 * @param collection - the complete collection to derive the window from
 * @param params - the query parameters of the request
 * @returns the collection response for the requested window
 */
function windowOfCollection(
  collection: Collection,
  params: URLSearchParams,
): Collection {
  let items = collection.items;

  const sort = params.get('sort');
  if (sort) {
    const specs = sort
      .split(',')
      .map((spec) => spec.trim())
      .filter(Boolean);
    items = [...items].sort((left, right) => {
      for (const spec of specs) {
        const descending = spec.startsWith('-');
        const field = descending ? spec.slice(1) : spec;
        const result = compareByField(left, right, field);
        if (result) return descending ? -result : result;
      }
      return 0;
    });
  }

  const total_count = items.length;
  const skip = Number(params.get('skip')) || 0;
  const limit = params.get('limit');
  if (skip || limit !== null) {
    items = items.slice(skip, limit === null ? undefined : skip + Number(limit));
  }

  return { ...collection, items, total_count };
}

/**
 * Create request handlers for the given responses
 *
 * This function takes a list of static responses for different endpoints and
 * converts it into a list of response handlers that can be used to setup MSW.
 * @param responses - a list of static responses
 * @returns a list of request handlers
 */
function createHandlersForResponses(responses: {
  [endpoint: string]: ResponseValue;
}): RequestHandler[] {
  const handlers: RequestHandler[] = [];

  type ResponseMap = { [params: string]: ResponseValue };

  const groupedResponses: { [endpoint: string]: ResponseMap } = {};

  /**
   * Collect responses with different query parameters for the same endpoint
   */
  Object.keys(responses).forEach((endpoint) => {
    let method, url;
    [method, url] = endpoint.split(' ');
    method = method.toLowerCase();
    if (!/^(get|post|patch|put|delete)$/.test(method)) {
      console.error('Invalid endpoint in fake data:', endpoint);
      return;
    }
    const urlParts = url.split('?');
    url = urlParts[0];
    const params = urlParts[1];
    const bareEndpoint = `${method} ${url}`;
    let responseMap = groupedResponses[bareEndpoint];
    if (!responseMap) {
      groupedResponses[bareEndpoint] = responseMap = {};
    }
    responseMap[params || '*'] = responses[endpoint];
  });

  /**
   * Find the response with the most matching parameters
   * @param request - the request that should be matched
   * @param responseMap - the map of responses to choose from
   * @returns the query string that matches the most parameters
   */
  async function getMatchingParamString(request: Request, responseMap: ResponseMap) {
    const paramStrings = Object.keys(responseMap);
    if (paramStrings.length < 2) {
      return paramStrings[0];
    }
    // combine parameters from query string and body
    const requestParams = new URL(request.url).searchParams;
    const method = request.method.toLowerCase();
    if (/post|patch|put|delete/.test(method)) {
      try {
        const bodyParams = await request.json();
        Object.entries(bodyParams).forEach(([key, value]) => {
          const paramValue = typeof value === 'string' ? value : JSON.stringify(value);
          requestParams.set(key, paramValue);
        });
      } catch {}
    }
    // find the response with the most matching parameters
    let bestParamString: string | null = null;
    let bestNumParams = 0;
    let bestStringLen = 0;
    Object.keys(responseMap).forEach((paramString) => {
      const params = new URLSearchParams(paramString);
      const numParams = Array.from(requestParams.keys()).reduce(
        (num, param) => num + (params.get(param) === requestParams.get(param) ? 1 : 0),
        0,
      );
      if (
        bestParamString === null ||
        numParams > bestNumParams ||
        (numParams === bestNumParams && paramString.length < bestStringLen)
      ) {
        bestParamString = paramString;
        bestNumParams = numParams;
        bestStringLen = paramString.length;
      }
    });
    return bestParamString;
  }

  /**
   * Create request handlers for the different endpoints
   */
  Object.keys(groupedResponses).forEach((endpoint) => {
    const [method, url] = endpoint.split(' ');
    const responseMap = groupedResponses[endpoint];
    /**
     * Resolver for the given endpoint
     * @param options - an options object containing the request
     * @param options.request - the request object
     * @returns - a response
     */
    const resolver = async ({ request }: { request: Request }) => {
      const paramString = await getMatchingParamString(request, responseMap);
      let response = responseMap[paramString || '*'];
      if (response === undefined) {
        console.debug('Not mocking', request.url);
        return;
      }
      if (Object.keys(responseMap).length > 1) {
        console.debug('Using mock data for params', paramString);
      }
      // Paginated list endpoints all share one convention (`sort`, `skip` and
      // `limit` over an `items` array), so instead of registering a fixture per
      // page and per sort order, a single fixture holding the whole collection is
      // narrowed down to whatever the request asks for. This is deliberately not
      // conditional on a `sort` parameter being present: the same code path also
      // implements plain pagination, and skipping it for unsorted requests would
      // return every entry on the first page.
      //
      // The exemption for entries that pin `skip` or `limit` in their key is what
      // lets an endpoint stay fully static: such a fixture is a canned window
      // rather than a complete collection, and narrowing it again would paginate
      // twice and report a total count of just that window.
      const matchedParams = new URLSearchParams(paramString ?? '');
      if (
        isCollection(response) &&
        !matchedParams.has('skip') &&
        !matchedParams.has('limit')
      ) {
        response = windowOfCollection(response, new URL(request.url).searchParams);
      }
      let status = 200;
      if (typeof response === 'number') {
        status = response;
        response = undefined;
      } else if (/post/.test(method)) {
        status = 201;
      } else if (/patch|put|delete/.test(method)) {
        status = 204;
      }
      if (DELAY && String(status)[0] === '2') {
        console.info(`Delaying response for ${DELAY} seconds...`);
        await new Promise((resolve) => setTimeout(resolve, DELAY * 1000));
      }
      return HttpResponse.json(response || undefined, { status });
    };
    const handler = http[method as keyof typeof http];
    if (!handler) {
      console.error('Unsupported method:', method);
    }
    handlers.push(handler.call(http, url, resolver));
  });

  return handlers;
}

/**
 * Create handlers that forward the given path
 * @param path - the path to forward
 * @returns a list of request handlers for this path
 */
function noMockHandler(path: string): RequestHandler[] {
  return [
    http.get(path, () => undefined),
    http.head(path, () => undefined),
    http.options(path, () => undefined),
    http.patch(path, () => undefined),
    http.post(path, () => undefined),
    http.put(path, () => undefined),
    http.delete(path, () => undefined),
  ];
}

/**
 * Create list of all response handlers for MSW
 */

export const handlers: RequestHandler[] = [];

const config = window.config;

if (config.mock_oidc) {
  handlers.push(...authHandlers);
} else {
  handlers.push(...noMockHandler('/api/auth/*'));
  handlers.push(...noMockHandler(config.oidc_authority_url + '*'));
}

if (config.mock_api) {
  handlers.push(...createHandlersForResponses(apiResponses));
  handlers.push(...noMockHandler('/@ng/*')); // hot module replacement
  handlers.push(...noMockHandler('/@fs/*')); // static files
  handlers.push(...noMockHandler('/chunk-*')); // code chunks
  handlers.push(...umamiHandlers); // umami tracker
} else {
  handlers.push(...noMockHandler('/*'));
}

handlers.push(...noMockHandler('https://cdn.jsdelivr.net/pyodide/*'));
handlers.push(...noMockHandler('https://pypi.org/simple/*'));
handlers.push(...noMockHandler('https://files.pythonhosted.org/packages/*'));
