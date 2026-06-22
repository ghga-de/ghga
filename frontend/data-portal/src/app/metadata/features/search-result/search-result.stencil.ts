/**
 * Stencil component for the individual search results in the metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';

/**
 * A stencil for the search results shown as a loading state.
 */
@Component({
  selector: 'app-search-result-stencil',
  imports: [MatExpansionModule, StencilComponent],
  templateUrl: './search-result.stencil.html',
  styleUrl: './search-result.stencil.scss',
})
export class SearchResultStencilComponent {}
