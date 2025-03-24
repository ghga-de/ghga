/**
 * These are the unit tests for the IVA type pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { IvaType } from '../models/iva';
import { IvaTypePipe } from './iva-type.pipe';

describe('IvaTypePipe', () => {
  it('can create an instance', () => {
    const pipe = new IvaTypePipe();
    expect(pipe).toBeTruthy();
  });

  it('should return {display: "SMS",typeAndValue: "SMS: +49123456789",icon: "smartphone"} for type Phone and value "49123456789"', () => {
    const pipe = new IvaTypePipe();
    const result = pipe.transform(IvaType['Phone'], '+49123456789');
    expect(result).toStrictEqual({
      display: 'SMS',
      typeAndValue: 'SMS: +49123456789',
      icon: 'smartphone',
    });
  });

  it('should return {display: "In Person",typeAndValue: "In Person: ",icon: "handshakes"} for type InPerson', () => {
    const pipe = new IvaTypePipe();
    const result = pipe.transform(IvaType['InPerson']);
    expect(result).toStrictEqual({
      display: 'In Person',
      typeAndValue: 'In Person: ',
      icon: 'handshakes',
    });
  });
});
