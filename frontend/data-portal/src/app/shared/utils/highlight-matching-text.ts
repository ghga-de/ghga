/**
 * This util takes a string and a substring to search, and returns an array of {text: string, highlighted: boolean}
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

/**
 * This function returns an array of {text: string, highlighted: boolean} based on a given string
 * and a substring to search for in the given string. Those parts of the given string that match
 * the substring, we highlight.
 *  @param str The string to search in
 * @param substr The substring to search
 * @returns An array of objects containing a substring and whether this substring should be highlighted
 */
export function highlightMatchingText(
  str: string,
  substr: string,
): { text: string; highlighted: boolean }[] {
  if (substr !== '') {
    return str
      .split(new RegExp(`(${substr})`, 'i'))
      .filter((x) => x)
      .map((x) => ({
        text: x,
        highlighted: x.toLocaleLowerCase() === substr.toLocaleLowerCase(),
      }));
  }
  return str ? [{ text: str, highlighted: false }] : [];
}
