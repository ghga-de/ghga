/**
 * Component for displaying search results in a list.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, output } from '@angular/core';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MetadataSearchService } from '@app/metadata/services/metadata-search.service';
import { SearchResultComponent } from '../search-result/search-result.component';
import { SearchResultStencilComponent } from '../search-result/search-result.stencil.component';

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];
const NUM_STENCILS = 3;

/**
 * Component for displaying search results in a list.
 */
@Component({
  selector: 'app-search-result-list',
  imports: [
    MatPaginatorModule,
    MatExpansionModule,
    MatProgressBarModule,
    SearchResultComponent,
    SearchResultStencilComponent,
  ],
  templateUrl: './search-result-list.component.html',
})
export class SearchResultListComponent {
  paginate = output<PageEvent>();
  #metadataSearch = inject(MetadataSearchService);
  results = this.#metadataSearch.searchResults;
  loading = this.#metadataSearch.searchResultsAreLoading;
  error = this.#metadataSearch.searchResultsError;
  pageSize = this.#metadataSearch.searchResultsLimit;
  pageIndex = computed(() => {
    const pageSize = this.pageSize();
    if (!pageSize) return 0;
    const skip = this.#metadataSearch.searchResultsSkip() ?? 0;
    return Math.floor(skip / pageSize);
  });
  pageSizeOptions = PAGE_SIZE_OPTIONS;

  numResults = computed(() => this.results().count);

  /**
   * Generate ids for the stencils
   * @yields the stencil id
   */
  *stencils() {
    for (let i = 0; i < NUM_STENCILS; ++i) {
      yield i;
    }
  }

  /**
   * Function to handle a change in pagination
   * @param e PageEvent instance
   */
  handlePageEvent(e: PageEvent) {
    this.paginate.emit(e);
  }
}
