/**
 * A shared directive that normalizes what is typed into an input
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Directive, ElementRef, inject, input } from '@angular/core';

/**
 * Directive that rewrites an input's text with the given normalizer on every
 * input event, keeping the caret where it was relative to the kept characters.
 *
 * A form model that normalizes its own value is not enough: when the normalized
 * value equals the previous one, as with a rejected character, the model does
 * not change and the form field never writes it back to the element.
 */
@Directive({
  selector: 'input[appNormalize]',
  host: { '(input)': 'onInput()' },
})
export class NormalizeInput {
  #el = inject<ElementRef<HTMLInputElement>>(ElementRef);

  /**
   * The function that maps the raw text to the text to show
   */
  readonly appNormalize = input.required<(value: string) => string>();

  /**
   * Replace the element's text with its normalized form if they differ
   */
  protected onInput(): void {
    const el = this.#el.nativeElement;
    const normalize = this.appNormalize();
    const value = el.value;
    const normalized = normalize(value);
    if (normalized === value) return;
    const caret = el.selectionStart ?? value.length;
    const newCaret = Math.min(
      normalize(value.slice(0, caret)).length,
      normalized.length,
    );
    el.value = normalized;
    if (el === el.ownerDocument.activeElement) el.setSelectionRange(newCaret, newCaret);
  }
}
