/**
 * A shared directive to mark external links
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  AfterViewInit,
  Directive,
  ElementRef,
  inject,
  input,
  Renderer2,
} from '@angular/core';

/**
 * Directive to mark external links
 *
 * This directive modifies anchor elements to:
 * - Add target="_blank" to open links in a new tab.
 * - Set rel="noreferrer noopener" for security.
 * - Set an aria-label indicating the link opens in a new tab for accessibility.
 *
 * An icon will be added automatically via the global style sheet.
 */
@Directive({
  selector: 'a[appExtLink]',
})
export class ExternalLinkDirective implements AfterViewInit {
  inline = input<boolean>(false);
  iconClasses = input<string>('');
  #el = inject(ElementRef);
  #renderer = inject(Renderer2);

  /**
   * After the view initializes, modify the anchor element
   */
  ngAfterViewInit() {
    const anchor: HTMLAnchorElement = this.#el.nativeElement;

    this.#renderer.setAttribute(anchor, 'target', '_blank');
    this.#renderer.setAttribute(anchor, 'rel', 'noreferrer noopener');

    const text = anchor.textContent?.trim() || '';
    this.#renderer.setAttribute(anchor, 'aria-label', `${text} (new tab)`);

    if (this.inline()) {
      this.#renderer.addClass(anchor, 'inline-ext-link');
    }
  }
}
