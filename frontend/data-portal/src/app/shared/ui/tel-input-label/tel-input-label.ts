/**
 * A shared directive that gives the phone input of ngx-mat-input-tel a name
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { afterRenderEffect, Directive, ElementRef, inject, input } from '@angular/core';
import { MAT_FORM_FIELD } from '@angular/material/form-field';

/**
 * Directive that gives the inner phone input of `ngx-mat-input-tel` an accessible name.
 *
 * The component offers no way to name its inner input: its `ariaLabel` input names
 * the country selector, and the `<mat-label>` of the form field points to the host
 * element, which cannot be labelled. So the input is linked to the label of the
 * enclosing form field, or named by the given text if there is no such label.
 * This relies on the component rendering a single `input[type=tel]`.
 */
@Directive({
  selector: 'ngx-mat-input-tel[appTelInputLabel]',
})
export class TelInputLabel {
  #el = inject<ElementRef<HTMLElement>>(ElementRef);
  #formField = inject(MAT_FORM_FIELD, { optional: true });

  /**
   * The name of the phone input if the form field has no label
   */
  readonly appTelInputLabel = input<string>('');

  /**
   * Link the phone input to the label, or name it directly
   */
  #labelEffect = afterRenderEffect(() => {
    const field = this.#el.nativeElement.querySelector('input[type="tel"]');
    if (!field) return;
    const labelId = this.#formField?.getLabelId();
    const label = this.appTelInputLabel();
    if (labelId) {
      field.setAttribute('aria-labelledby', labelId);
      field.removeAttribute('aria-label');
    } else if (label) {
      field.setAttribute('aria-label', label);
      field.removeAttribute('aria-labelledby');
    }
  });
}
