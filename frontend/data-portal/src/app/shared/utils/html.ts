/**
 * Helper functions for building HTML strings
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

const HTML_ENTITIES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
};

/**
 * Escape text so that it can be inserted into an HTML string verbatim.
 * @param text - the text to escape, e.g. a file name chosen by a user
 * @returns the text with all HTML special characters replaced by entities
 */
export function escapeHtml(text: string): string {
  return text.replace(/[&<>"']/g, (char) => HTML_ENTITIES[char]);
}

/**
 * HTML markup built with the `html` tag, as opposed to a plain string,
 * which is always treated as text.
 */
export class Html {
  /**
   * Wrap markup that is known to be safe
   * @param markup - the HTML markup
   */
  constructor(readonly markup: string) {}

  /**
   * Return the markup, so that the object can be interpolated
   * @returns the HTML markup
   */
  toString(): string {
    return this.markup;
  }
}

/**
 * Tag for template literals that builds HTML markup, escaping every
 * interpolated value except values that are themselves built with this tag.
 * Prettier reflows the markup of such templates, so runs of whitespace in the
 * literal parts are collapsed to one space, as HTML renders them anyway.
 * @param strings - the literal parts of the template, taken as markup
 * @param values - the interpolated values, taken as text
 * @returns the HTML markup
 */
export function html(strings: TemplateStringsArray, ...values: unknown[]): Html {
  const literals = strings.map((literal) => literal.replace(/\s+/g, ' '));
  literals[0] = literals[0].trimStart();
  literals[literals.length - 1] = literals[literals.length - 1].trimEnd();
  let markup = literals[0];
  values.forEach((value, index) => {
    markup += value instanceof Html ? value.markup : escapeHtml(String(value));
    markup += literals[index + 1];
  });
  return new Html(markup);
}

/**
 * Get the markup for content that is either HTML or plain text.
 * @param content - HTML built with the `html` tag, or plain text
 * @returns the HTML markup, with plain text escaped
 */
export function toMarkup(content: Html | string): string {
  return content instanceof Html ? content.markup : escapeHtml(content);
}
