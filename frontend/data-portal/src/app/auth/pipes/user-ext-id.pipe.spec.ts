/**
 * Unit tests for UserExtIdPipe
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { UserExtIdPipe } from './user-ext-id.pipe';

describe('UserExtIdPipe', () => {
  let pipe: UserExtIdPipe;

  beforeEach(() => {
    pipe = new UserExtIdPipe();
  });

  it('should create an instance', () => {
    expect(pipe).toBeTruthy();
  });

  it('should remove default suffix from external ID', () => {
    const extId = 'fred.flintstone@lifescience-ri.eu';
    const result = pipe.transform(extId);
    expect(result).toBe('fred.flintstone');
  });

  it('should return unchanged value when suffix is not present', () => {
    const extId = 'fred.flintston@test.dev';
    const result = pipe.transform(extId);
    expect(result).toBe('fred.flintston@test.dev');
  });

  it('should return unchanged value when suffix is 0', () => {
    const extId = 'fred@test.dev';
    const result = pipe.transform(extId);
    expect(result).toBe('fred@test.dev');
  });

  it('should handle empty string', () => {
    const result = pipe.transform('');
    expect(result).toBe('');
  });

  it('should handle null value', () => {
    const result = pipe.transform(null);
    expect(result).toBe('');
  });

  it('should handle undefined value', () => {
    const result = pipe.transform(undefined);
    expect(result).toBe('');
  });

  it('should shorten result when maxChars is specified and exceeded', () => {
    const extId = 'verylongusername@lifescience-ri.eu';
    const result = pipe.transform(extId, 8);
    expect(result).toBe('verylong...');
  });

  it('should not shorten result when maxChars is specified but not exceeded', () => {
    const extId = 'short@lifescience-ri.eu';
    const result = pipe.transform(extId, 10);
    expect(result).toBe('short');
  });

  it('should work with maxChars on external ID without default suffix', () => {
    const extId = 'verylongusername@test.dev';
    const result = pipe.transform(extId, 12);
    expect(result).toBe('verylonguser...');
  });

  it('should handle edge case where maxChars equals result length', () => {
    const extId = 'user@lifescience-ri.eu';
    const result = pipe.transform(extId, 4);
    expect(result).toBe('user');
  });
});
