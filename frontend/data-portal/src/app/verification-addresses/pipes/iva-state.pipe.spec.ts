/**
 * These are the unit tests for the IVA state pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { IvaState } from '../models/iva';
import { IvaStatePipe } from './iva-state.pipe';

describe('IvaStatePipe', () => {
  it('can create an instance', () => {
    const pipe = new IvaStatePipe();
    expect(pipe).toBeTruthy();
  });

  it('should show "None" for an empty state', () => {
    const pipe = new IvaStatePipe();
    for (const state of [null, undefined, '']) {
      const result = pipe.transform(state as unknown as IvaState);
      expect(result).toStrictEqual({ name: 'None', class: 'text-error' });
    }
  });

  it('should show the state itself for an unknown state', () => {
    const pipe = new IvaStatePipe();
    const result = pipe.transform('Unknown state' as IvaState);
    expect(result).toStrictEqual({ name: 'Unknown state', class: 'text-error' });
  });

  it('should work properly for the CodeRequested state', () => {
    const pipe = new IvaStatePipe();
    const result = pipe.transform(IvaState.CodeRequested);
    expect(result).toStrictEqual({ name: 'Code Requested', class: 'text-warning' });
  });

  it('should work properly for the CodeRequested state', () => {
    const pipe = new IvaStatePipe();
    const result = pipe.transform(IvaState.Verified);
    expect(result).toStrictEqual({ name: 'Verified', class: 'text-success' });
  });
});
