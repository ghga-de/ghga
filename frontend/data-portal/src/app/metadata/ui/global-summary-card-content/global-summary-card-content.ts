/**
 * UI component for displaying the global summary badge contents
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DecimalPipe } from '@angular/common';
import { Component, input } from '@angular/core';
import { ValueCount } from '@app/metadata/models/global-summary';
import { UnderscoreToSpace as UnderscoreToSpacePipe } from '@app/shared/pipes/underscore-to-space-pipe';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';

/**
 * Component for the global summary badge contents
 */
@Component({
  selector: 'app-global-summary-card-content',
  templateUrl: './global-summary-card-content.html',
  imports: [UnderscoreToSpacePipe, DecimalPipe, StencilComponent],
})
export class GlobalSummaryCardContentComponent {
  readonly isLoading = input.required<boolean>();
  readonly data = input<ValueCount[]>();
  readonly caption = input.required<string>();
  readonly propertyName = input.required<string>();
}
