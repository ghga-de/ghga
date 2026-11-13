/**
 * Unit tests for the verification code generator
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { generateVerificationCode } from './verification-code';

describe('generateVerificationCode', () => {
  it('should generate codes of six characters by default', () => {
    expect(generateVerificationCode()).toHaveLength(6);
  });

  it('should generate codes of the given size', () => {
    expect(generateVerificationCode(9)).toHaveLength(9);
  });

  it('should use only unambiguous letters and digits', () => {
    for (let i = 0; i < 100; i++) {
      const code = generateVerificationCode();
      expect(code).toMatch(/^[2-9A-HJ-NP-Z]{6}$/);
      expect(code.replace(/\d/g, '').length).toBeGreaterThanOrEqual(2);
      expect(code.replace(/\D/g, '').length).toBeGreaterThanOrEqual(2);
    }
  });

  it('should generate different codes', () => {
    const codes = new Set(Array.from({ length: 20 }, () => generateVerificationCode()));
    expect(codes.size).toBeGreaterThan(1);
  });
});
