/**
 * A stencil component for dataset summaries in the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link.directive';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil.component';

/**
 * A stencil component for dataset summaries used as a loading state
 */
@Component({
  selector: 'app-dataset-summary-stencil',
  imports: [
    MatIconModule,
    MatButtonModule,
    MatChipsModule,
    StencilComponent,
    ExternalLinkDirective,
  ],
  templateUrl: './dataset-summary.stencil.component.html',
})
export class DatasetSummaryStencilComponent {}
