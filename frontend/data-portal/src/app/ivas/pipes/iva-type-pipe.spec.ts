/**
 * These are the unit tests for the IVA type pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { IvaType } from '../models/iva';
import { IvaTypePipe } from './iva-type-pipe';

describe('IvaTypePipe', () => {
  it('can create an instance', () => {
    const pipe = new IvaTypePipe();
    expect(pipe).toBeTruthy();
  });

  it('should show "None" for an empty type', () => {
    const pipe = new IvaTypePipe();
    for (const type of [null, undefined, '']) {
      const result = pipe.transform(type as unknown as IvaType);
      expect(result).toStrictEqual({ name: 'None', icon: 'warning' });
    }
  });

  it('should show the type itself for an unknown type', () => {
    const pipe = new IvaTypePipe();
    const result = pipe.transform('Unknown type' as IvaType);
    expect(result).toStrictEqual({ name: 'Unknown type', icon: 'warning' });
  });

  it('should properly transform the Phone type', () => {
    const pipe = new IvaTypePipe();
    const result = pipe.transform(IvaType['Phone']);
    expect(result).toStrictEqual({
      name: 'SMS',
      icon: 'smartphone',
    });
  });

  it('should properly transform the InPerson type', () => {
    const pipe = new IvaTypePipe();
    const result = pipe.transform(IvaType['InPerson']);
    expect(result).toStrictEqual({
      name: 'In Person',
      icon: 'handshakes',
    });
  });
});
