/**
 * Metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { ConfigService } from '@app/shared/services/config';
import { NotificationService } from '@app/shared/services/notification';
import { MetadataBrowserFilterComponent } from '../metadata-browser-filter/metadata-browser-filter';
import { SearchResultListComponent } from '../search-result-list/search-result-list';

/**
 * This is the metadata browser component
 */
@Component({
  selector: 'app-metadata-browser',
  imports: [
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    SearchResultListComponent,
    MatCardModule,
    MetadataBrowserFilterComponent,
  ],
  templateUrl: './metadata-browser.html',
})
export class MetadataBrowserComponent {
  #config = inject(ConfigService);
  #notify = inject(NotificationService);
  #metadataSearch = inject(MetadataSearchService);
  #max_facet_options = this.#config.maxFacetOptions;

  #searchResults = this.#metadataSearch.searchResultsResource;
  #searchResultsError = this.#searchResults.error;
  protected status = this.#searchResults.status;
  protected searchResults = this.#searchResults.value;
  protected facets = computed(() =>
    this.searchResults().facets.filter(
      (f) => f.options.length > 0 && f.options.length <= this.#max_facet_options,
    ),
  );
  protected numResults = computed(() => this.searchResults().count);
  protected loading = computed(() => this.#searchResults.isLoading());

  protected errorMessage = computed(() => {
    if (this.#searchResultsError()) {
      switch ((this.#searchResultsError() as HttpErrorResponse)?.status) {
        case undefined:
          return undefined;
        default:
          return 'There was an error browsing the datasets. Please try again later.';
      }
    } else return undefined;
  });

  #errorEffect = effect(() => {
    if (this.#metadataSearch.searchResultsResource.error()) {
      this.#notify.showError('Error fetching search results.');
    }
  });
}
