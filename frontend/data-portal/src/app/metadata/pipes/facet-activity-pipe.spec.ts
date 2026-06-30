/**
 * These are the unit tests for the FacetActivity pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { FacetActivityPipe } from './facet-activity-pipe';

describe('FacetActivityPipe', () => {
  it('can create an instance', () => {
    const pipe = new FacetActivityPipe();
    expect(pipe).toBeTruthy();
  });

  it('returns true for an active facet', () => {
    const pipe = new FacetActivityPipe();
    const facetState = { name: ['value'] };
    expect(pipe.transform('name#value', facetState)).toBe(true);
  });

  it('returns false for an inactive facet', () => {
    const pipe = new FacetActivityPipe();
    const facetState = { name1: ['value1'], name2: ['value2', 'value3'] };
    expect(pipe.transform('name3#value4', facetState)).toBe(false);
  });

  it('returns false for an incorrect facet request', () => {
    const pipe = new FacetActivityPipe();
    const facetState = { name: ['value'] };
    expect(pipe.transform('bad_value', facetState)).toBe(false);
  });
});
