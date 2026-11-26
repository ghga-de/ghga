/**
 * Tests for the HTML helper functions.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { escapeHtml, Html, html, toMarkup } from './html';

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

describe('html', () => {
  it('should keep the literal markup and escape interpolated values', () => {
    const name = '<b>Tom</b> & Jerry';
    expect(html`<p>${name}</p>`.markup).toBe(
      '<p>&lt;b&gt;Tom&lt;/b&gt; &amp; Jerry</p>',
    );
  });

  it('should not escape nested markup built with the tag', () => {
    const inner = html`<strong>${'a<b'}</strong>`;
    expect(html`<p>${inner}</p>`.markup).toBe('<p><strong>a&lt;b</strong></p>');
  });

  it('should collapse whitespace in the markup but not in values', () => {
    const value = ' a  b ';
    // prettier-ignore
    const markup = html`
      <p>
        ${value}
      </p>
    `.markup;
    expect(markup).toBe('<p>  a  b  </p>');
  });

  it('should convert other values to text', () => {
    expect(html`${42} ${null}`.markup).toBe('42 null');
  });
});

describe('toMarkup', () => {
  it('should escape plain text', () => {
    expect(toMarkup('<b>x</b>')).toBe('&lt;b&gt;x&lt;/b&gt;');
  });

  it('should keep markup built with the html tag', () => {
    expect(toMarkup(new Html('<b>x</b>'))).toBe('<b>x</b>');
  });
});
