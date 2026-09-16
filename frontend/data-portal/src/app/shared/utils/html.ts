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
