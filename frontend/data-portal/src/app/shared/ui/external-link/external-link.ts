/**
 * A shared directive to mark external links
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { AfterViewInit, Directive, ElementRef, inject, Renderer2 } from '@angular/core';

/**
 * Directive to mark external links
 *
 * This directive modifies anchor elements to:
 * - Add target="_blank" to open links in a new tab.
 * - Set rel="noreferrer noopener" for security.
 * - Set an aria-label indicating the link opens in a new tab for accessibility.
 * - Wrap text nodes in span elements for styling purposes.
 *
 * An icon will be added automatically via the global style sheet.
 */
@Directive({
  selector: 'a[appExtLink]',
})
export class ExternalLinkDirective implements AfterViewInit {
  #el = inject(ElementRef);
  #renderer = inject(Renderer2);

  /**
   * Get normalized visible text for the host anchor.
   * @param anchor - the host anchor element
   * @returns normalized visible text of the anchor
   */
  #anchorText(anchor: HTMLAnchorElement): string {
    return (anchor.textContent || '').replace(/\s+/g, ' ').trim();
  }

  /**
   * Wrap non-empty direct text nodes in span elements to allow styling.
   * Existing child elements are preserved.
   * @param anchor - the host anchor element
   */
  #wrapTextNodes(anchor: HTMLAnchorElement): void {
    const children = Array.from(anchor.childNodes);

    for (const child of children) {
      if (child.nodeType !== Node.TEXT_NODE) {
        continue;
      }

      const text = child.textContent || '';
      const normalizedText = text.replace(/\s+/g, ' ').trim();

      if (!normalizedText) {
        this.#renderer.removeChild(anchor, child);
        continue;
      }

      const span = this.#renderer.createElement('span');
      this.#renderer.setProperty(span, 'textContent', normalizedText);
      this.#renderer.insertBefore(anchor, span, child);
      this.#renderer.removeChild(anchor, child);
    }
  }

  /**
   * After the view initializes, modify the anchor element
   */
  ngAfterViewInit() {
    const anchor: HTMLAnchorElement = this.#el.nativeElement;

    this.#renderer.setAttribute(anchor, 'target', '_blank');
    this.#renderer.setAttribute(anchor, 'rel', 'noreferrer noopener');

    const text = this.#anchorText(anchor);
    const currentAriaLabel = anchor.getAttribute('aria-label');

    if (!currentAriaLabel && text) {
      this.#renderer.setAttribute(anchor, 'aria-label', `${text} (new tab)`);
    }

    this.#wrapTextNodes(anchor);
  }
}
