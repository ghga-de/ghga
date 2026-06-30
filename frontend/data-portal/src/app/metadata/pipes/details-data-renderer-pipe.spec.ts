/**
 * These are the unit tests for the DetailsDataRenderer pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DetailsDataRendererPipe } from './details-data-renderer-pipe';

describe('DetailsDataRendererPipe', () => {
  it('can create an instance', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe).toBeTruthy();
  });

  it('returns N/A for an undefined value', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('test', undefined, 'accessor')).toBe('N/A');
  });

  it('returns N/A for a non-existent accessor', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('test', { wrong_accessor: 'test value' }, 'accessor')).toBe(
      'N/A',
    );
  });

  it('returns the value for an empty value string', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('test', { accessor: '' }, 'accessor')).toBe('');
  });

  it('returns the value for a defined value', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('test', { accessor: 'test value' }, 'accessor')).toBe(
      'test value',
    );
  });

  it('returns the value for a nested accessor', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(
      pipe.transform(
        'test',
        { accessor: { test: { me: 'test value' } } },
        'accessor.test.me',
      ),
    ).toBe('test value');
  });

  it('returns the comma-separated list of an array of phenotypes', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(
      pipe.transform('phenotype', { accessor: ['test', 'value'] }, 'accessor'),
    ).toBe('test, value');
  });

  it('returns the value of a single phenotype', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('phenotype', { accessor: ['test value'] }, 'accessor')).toBe(
      'test value',
    );
  });

  it("returns the value of a file's origin with spaces instead of underscores and with the first letter capitalised", () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('origin', { accessor: 'test_value' }, 'accessor')).toBe(
      'Test value',
    );
  });

  it('returns the properly aliased file location', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(
      pipe.transform('location', { accessor: 'test_location' }, 'accessor', {
        test_location: 'test value',
      }),
    ).toBe('test value');
  });

  it('returns the original value of the location when no alias is found', () => {
    const pipe = new DetailsDataRendererPipe();
    expect(
      pipe.transform('location', { accessor: 'test_location' }, 'accessor', {
        wrong_location: 'test value',
      }),
    ).toBe('test_location');
  });

  it("returns the properly capitalised value of a sample's biological sex", () => {
    const pipe = new DetailsDataRendererPipe();
    expect(pipe.transform('sex', { accessor: 'TEST' }, 'accessor')).toBe('Test');
  });
});
