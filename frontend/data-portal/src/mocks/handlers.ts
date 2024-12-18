/**
 * Mock REST handlers
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { http, HttpResponse, RequestHandler } from 'msw';
import { handlers as authHandlers } from './auth';
import { responses, ResponseValue } from './responses';

/**
 * This module takes a list of static responses for different endpoints and
 * converts it into a list of response handlers that can be used to setup MSW.
 */

/**
 * List of handlers for REST endpoints
 */
export const handlers: RequestHandler[] = [...authHandlers];

type ResponseMap = { [params: string]: ResponseValue };

const groupedResponses: { [endpoint: string]: ResponseMap } = {};

/**
 * Collect responses with different query parameters for the same endpoint
 */
Object.keys(responses).forEach((endpoint) => {
  let method, url, params;
  [method, url] = endpoint.split(' ');
  method = method.toLowerCase();
  if (!/^(get|post|patch|put|delete)$/.test(method)) {
    console.error('Invalid endpoint in fake data:', endpoint);
    return;
  }
  [url, params] = url.split('?');
  let bareEndpoint = `${method} ${url}`;
  let responseMap = groupedResponses[bareEndpoint];
  if (!responseMap) {
    groupedResponses[bareEndpoint] = responseMap = {};
  }
  responseMap[params || '*'] = responses[endpoint];
});

/**
  Find the response with the most matching parameters
  @param request - the request that should be matched
  @param responseMap - the map of responses to choose from
  @returns the query string that matches the most parameters
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

// create request handlers for the different endpoints
Object.keys(groupedResponses).forEach((endpoint) => {
  let method, url;
  [method, url] = endpoint.split(' ');
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
      console.debug('Not mocking', url);
      return;
    }
    if (Object.keys(responseMap).length > 1) {
      console.debug('Using mock data for params', paramString);
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
    return HttpResponse.json(response || undefined, { status });
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handler = (http as any)[method];
  if (!handler) {
    console.error('Unsupported method:', method);
  }
  handlers.push(handler.call(http, url, resolver));
});
