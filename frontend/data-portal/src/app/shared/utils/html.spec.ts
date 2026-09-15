/**
 * Tests for the HTML helper functions.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { escapeHtml } from './html';

describe('escapeHtml', () => {
  it('should leave plain text unchanged', () => {
    expect(escapeHtml('sample_1.fastq.gz')).toBe('sample_1.fastq.gz');
  });

  it('should escape all HTML special characters', () => {
    expect(escapeHtml(`<b>"Tom" & 'Jerry'</b>`)).toBe(
      '&lt;b&gt;&quot;Tom&quot; &amp; &#39;Jerry&#39;&lt;/b&gt;',
    );
  });
});
