/**
 * Test the error handling utilities.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { getBackendErrorMessage } from './errors';

describe('getBackendErrorMessage', () => {
  it('should return an empty string for non-error types', () => {
    expect(getBackendErrorMessage(null)).toBe('');
    expect(getBackendErrorMessage(undefined)).toBe('');
    expect(getBackendErrorMessage(42)).toBe('');
    expect(getBackendErrorMessage({})).toBe('');
  });

  it('should return the string itself for an error that is a string', () => {
    const msg = 'some string error';
    const result = getBackendErrorMessage(msg);
    expect(result).toBe(msg);
  });

  it('should return the details with highest priority', () => {
    const msg = 'some detailed error';
    expect(
      getBackendErrorMessage({
        error: { detail: msg },
        status: 500,
        statusText: 'some error',
        message: 'some error',
      }),
    ).toBe(msg);
  });

  it('should handle errors created by Pydantic', () => {
    const msg = 'some detailed error';
    expect(
      getBackendErrorMessage({
        error: { detail: [{ msg }, { msg: 'another error' }] },
        status: 422,
        statusText: 'some error',
        message: 'some error',
      }),
    ).toBe(msg);
  });

  it('should ignore other types of details', () => {
    expect(
      getBackendErrorMessage({
        error: { detail: {} as unknown as string },
        status: 500,
        message: 'some error',
      }),
    ).toBe('some error');
    expect(
      getBackendErrorMessage({
        error: { detail: {} as unknown as string },
        status: 500,
        message: {} as unknown as string,
      }),
    ).toBe('');
  });

  it('should return the status text with second highest priority', () => {
    const msg = 'some detailed error';
    expect(
      getBackendErrorMessage({
        status: 500,
        statusText: msg,
        message: 'some error',
      }),
    ).toBe(msg);
    expect(
      getBackendErrorMessage({
        error: { detail: '' },
        status: 500,
        statusText: msg,
        message: 'some error',
      }),
    ).toBe(msg);
  });

  it('should return the message text with lowest priority', () => {
    const msg = 'some detailed error';
    expect(
      getBackendErrorMessage({
        status: 500,
        message: msg,
      }),
    ).toBe(msg);
    expect(
      getBackendErrorMessage({
        error: { detail: '' },
        status: 500,
        statusText: '',
        message: msg,
      }),
    ).toBe(msg);
  });

  it('should remove superfluous quotes', () => {
    expect(
      getBackendErrorMessage({
        error: { detail: '"some error"' },
        status: 500,
      }),
    ).toBe('some error');
    expect(
      getBackendErrorMessage({
        status: 500,
        message: "'some error'",
      }),
    ).toBe('some error');
  });

  it('should keep non-matching quotes', () => {
    let msg = '"some error\'';
    expect(
      getBackendErrorMessage({
        error: { detail: msg },
        status: 500,
      }),
    ).toBe(msg);
    msg = '\'some error"';
    expect(
      getBackendErrorMessage({
        status: 500,
        message: msg,
      }),
    ).toBe(msg);
  });
});
