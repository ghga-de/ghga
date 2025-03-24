/**
 * Test the name initials pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { InitialsPipe } from './initials.pipe';

describe('InitialsPipe', () => {
  it('can create an instance', () => {
    const pipe = new InitialsPipe();
    expect(pipe).toBeTruthy();
  });

  it('returns null if passed null or undefined', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform(null)).toBeNull();
    expect(pipe.transform(undefined)).toBeNull();
  });

  it('returns null if passed empty name or only whitespace', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('')).toBeNull();
    expect(pipe.transform(' ')).toBeNull();
    expect(pipe.transform('   ')).toBeNull();
  });

  it('should return just one initial if there is only one name', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('alice')).toBe('A');
    expect(pipe.transform(' bob ')).toBe('B');
    expect(pipe.transform('  charlie  ')).toBe('C');
  });

  it('should return both initials if there are two names', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('alice brown')).toBe('AB');
    expect(pipe.transform(' charlie dork ')).toBe('CD');
    expect(pipe.transform('  eva   fudd  ')).toBe('EF');
  });

  it('should first and last initial if there are more than two names', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('alice cleo brown')).toBe('AB');
    expect(pipe.transform(' charlie elon dork ')).toBe('CD');
    expect(pipe.transform('  eva  gabriela  hazel  fudd  ')).toBe('EF');
    expect(pipe.transform('goofy a b c d e f g hobbleton')).toBe('GH');
  });

  it('does not change case if names are already capitalized', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('Alice Brown')).toBe('AB');
  });

  it('works with all kinds of whitespace', () => {
    const pipe = new InitialsPipe();
    expect(pipe.transform('alice\u00a0brown')).toBe('AB');
    expect(pipe.transform('alice\tbrown')).toBe('AB');
    expect(pipe.transform('alice \t \u00a0 \r \n brown')).toBe('AB');
  });
});
