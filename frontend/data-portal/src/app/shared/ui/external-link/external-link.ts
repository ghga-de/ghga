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
 * - Wrap the link text in a span for styling purposes.
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
   * After the view initializes, modify the anchor element
   */
  ngAfterViewInit() {
    const anchor: HTMLAnchorElement = this.#el.nativeElement;

    this.#renderer.setAttribute(anchor, 'target', '_blank');
    this.#renderer.setAttribute(anchor, 'rel', 'noreferrer noopener');

    // Get original text content
    const text = anchor.textContent?.trim() || '';

    // Create a suitable aria-label to explain the meaning of the icon
    this.#renderer.setAttribute(anchor, 'aria-label', `${text} (new tab)`);

    // Wrap text content in a span so that it can be styled separately
    const span = this.#renderer.createElement('span');
    this.#renderer.setProperty(span, 'textContent', text);
    this.#renderer.setProperty(anchor, 'textContent', '');
    this.#renderer.appendChild(anchor, span);
  }
}
