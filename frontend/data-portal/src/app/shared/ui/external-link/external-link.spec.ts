/**
 * Test the external link directive
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';
import { ExternalLink } from './external-link';

/**
 * Create an anchor with the directive applied
 * @param content - the inner HTML of the anchor
 * @param ariaLabel - an aria-label the anchor already has
 * @returns the anchor element
 */
async function createLink(
  content: string,
  ariaLabel?: string,
): Promise<HTMLAnchorElement> {
  const fixture = TestBed.createDirective(ExternalLink, { tagName: 'a' });
  const anchor = fixture.nativeElement as HTMLAnchorElement;
  anchor.innerHTML = content;
  if (ariaLabel) anchor.setAttribute('aria-label', ariaLabel);
  await fixture.whenStable();
  return anchor;
}

describe('ExternalLink', () => {
  it('should add target="_blank"', async () => {
    const anchor = await createLink('Test Link');
    expect(anchor.getAttribute('target')).toBe('_blank');
  });

  it('should set aria-label with (new tab)', async () => {
    const anchor = await createLink('Test Link');
    expect(anchor.getAttribute('aria-label')).toBe('Test Link (new tab)');
  });

  it('should add rel="noreferrer noopener"', async () => {
    const anchor = await createLink('Test Link');
    expect(anchor.getAttribute('rel')).toBe('noreferrer noopener');
  });

  it('should preserve existing child elements', async () => {
    const anchor = await createLink('<span class="icon"></span>GHGA Website');
    expect(anchor.querySelector('.icon')).not.toBeNull();
    expect(anchor.textContent).toContain('GHGA Website');
  });

  it('should preserve existing aria-label', async () => {
    const anchor = await createLink('Docs', 'Custom Label');
    expect(anchor.getAttribute('aria-label')).toBe('Custom Label');
  });
});
