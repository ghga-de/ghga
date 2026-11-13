/**
 * Generator for random verification codes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

// same alphabet as the IVA codes of the auth service, without 0, 1, I and O
const CODE_DIGITS = '23456789';
const CODE_LETTERS = 'ABCDEFGHJKLMNPQRSTUVWXYZ';
const CODE_CHARS = CODE_DIGITS + CODE_LETTERS;

/**
 * Pick a random character from the given string using a secure random generator.
 * @param chars - the characters to pick from
 * @returns one of the characters
 */
function randomChar(chars: string): string {
  const [value] = crypto.getRandomValues(new Uint32Array(1));
  return chars[value % chars.length];
}

/**
 * Generate a random verification code like the IVA codes of the auth service.
 * A third of the characters are letters, a third digits, the rest either.
 * @param size - the length of the code
 * @returns the generated code
 */
export function generateVerificationCode(size = 6): string {
  const third = Math.floor(size / 3);
  const chars = [
    ...Array.from({ length: third }, () => randomChar(CODE_LETTERS)),
    ...Array.from({ length: third }, () => randomChar(CODE_DIGITS)),
    ...Array.from({ length: size - 2 * third }, () => randomChar(CODE_CHARS)),
  ];
  // shuffle with Fisher-Yates
  for (let i = chars.length - 1; i > 0; i--) {
    const j = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1);
    [chars[i], chars[j]] = [chars[j], chars[i]];
  }
  return chars.join('');
}
