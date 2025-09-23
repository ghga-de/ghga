/**
 * Metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, effect, inject, OnInit, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxChange, MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { PageEvent } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, Router } from '@angular/router';
import { FacetFilterSetting } from '@app/metadata/models/facet-filter';
import { FacetActivityPipe } from '@app/metadata/pipes/facet-activity.pipe';
import { MetadataSearchService } from '@app/metadata/services/metadata-search.service';
import { ConfigService } from '@app/shared/services/config.service';
import { NotificationService } from '@app/shared/services/notification.service';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil.component';
import { SearchResultListComponent } from '../search-result-list/search-result-list.component';

const DEFAULT_PAGE_SIZE = 10;
const DEFAULT_SKIP_VALUE = 0;

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
    FacetActivityPipe,
    SearchResultListComponent,
    StencilComponent,
    MatCardModule,
  ],
  templateUrl: './metadata-browser.component.html',
})
export class MetadataBrowserComponent implements OnInit {
  #config = inject(ConfigService);
  #notify = inject(NotificationService);
  #metadataSearch = inject(MetadataSearchService);
  #route = inject(ActivatedRoute);
  #router = inject(Router);
  #className = 'EmbeddedDataset';
  #skip = DEFAULT_SKIP_VALUE;
  #pageSize = DEFAULT_PAGE_SIZE;
  #max_facet_options = this.#config.maxFacetOptions;

  facetData = signal<FacetFilterSetting>({});
  searchFormControl = new FormControl('');
  searchFormGroup = new FormGroup({
    searchTerm: this.searchFormControl,
  });
  searchTerm = '';
  lastSearchQuery = this.#metadataSearch.query;
  lastSearchFilterFacets = this.#metadataSearch.facets;
  #searchResults = this.#metadataSearch.searchResults;
  #searchResultsError = this.#searchResults.error;
  status = this.#searchResults.status;
  searchResults = this.#searchResults.value;
  facets = computed(() =>
    this.searchResults().facets.filter(
      (f) => f.options.length > 0 && f.options.length <= this.#max_facet_options,
    ),
  );
  numResults = computed(() => this.searchResults().count);
  loading = computed(() => this.#searchResults.isLoading());

  errorMessage = computed(() => {
    if (this.#searchResultsError()) {
      switch ((this.#searchResultsError() as HttpErrorResponse)?.status) {
        case undefined:
          return undefined;
        default:
          return 'There was an error browsing the datasets. Please try again later.';
      }
    } else return undefined;
  });

  displayFilters = false;

  /**
   * On init, define the default values of the search variables
   */
  ngOnInit(): void {
    this.#loadSearchTermsFromRoute();
  }

  /**
   * This function takes the current URL, determines the query parameters and sets them accordingly in the metadata search service.
   */
  #loadSearchTermsFromRoute(): void {
    const { s, q, f, p } = this.#router.routerState.snapshot.root.queryParams;
    this.#pageSize = parseInt(p) || DEFAULT_PAGE_SIZE;
    this.searchTerm = q || '';
    if (f) {
      const paramVals = this.#facetDataFromString(decodeURIComponent(f));
      if (paramVals) {
        this.facetData.set(paramVals);
      }
    }
    this.#skip = parseInt(s) || DEFAULT_SKIP_VALUE;
    this.#metadataSearch.loadQueryParameters(
      this.#className,
      this.#pageSize,
      this.#skip,
      this.searchTerm,
      this.facetData(),
    );
    this.searchFormControl.setValue(this.searchTerm);
  }

  /**
   * Syncs the data between this component and the search service and initiates a new search.
   */
  #performSearch(): void {
    this.#updateMetadataServiceSearchTermsAndRoute();
  }

  /**
   * Pushes the local filters, search term and page setup to the search service.
   */
  async #updateMetadataServiceSearchTermsAndRoute(): Promise<void> {
    await this.#router.navigate([], {
      relativeTo: this.#route,
      queryParams: {
        s: this.#skip !== DEFAULT_SKIP_VALUE ? this.#skip : undefined,
        q: this.searchTerm !== '' ? this.searchTerm : undefined,
        f:
          Object.keys(this.facetData()).length !== 0
            ? encodeURIComponent(this.#facetDataToString(this.facetData()))
            : undefined,
        p: this.#pageSize !== DEFAULT_PAGE_SIZE ? this.#pageSize : undefined,
      },
    });
    this.#loadSearchTermsFromRoute();
  }

  /**
   * Sets the parameters for the search and triggers it in the metadataSearch Service
   * @param event we need to stop the event from propagating
   */
  submit(event: MouseEvent | SubmitEvent | Event): void {
    event.preventDefault();
    const searchTerm = this.searchFormControl.value || '';
    if (searchTerm !== this.searchTerm || this.#facetDataChanged()) {
      this.searchTerm = searchTerm;
      this.#skip = DEFAULT_SKIP_VALUE;
      this.#performSearch();
    }
  }

  /**
   * Handles the click event on a facet filter that was active in the last search (as shown above the search results)
   * @param facetToRemove The facet name and option to remove.
   */
  removeFacet(facetToRemove: string): void {
    const facetToRemoveSplit = facetToRemove.split('#');
    if (facetToRemoveSplit.length !== 2) return;
    this.#updateFacets(facetToRemoveSplit[0], facetToRemoveSplit[1], false);
    this.#skip = DEFAULT_SKIP_VALUE;
    this.#performSearch();
  }

  /**
   * Resets the search query and triggers a reload of the results.
   */
  clearSearchQuery(): void {
    if (
      this.searchTerm !== '' ||
      this.searchFormControl.value ||
      this.#facetDataChanged()
    ) {
      this.searchTerm = '';
      this.searchFormControl.setValue('');
      this.#skip = DEFAULT_SKIP_VALUE;
      this.#performSearch();
    }
  }

  /**
   * Clears the search field input and triggers a result update
   * @param event we need to stop the event from propagating
   */
  clear(event: MouseEvent): void {
    event.preventDefault();
    this.facetData.set({});
    this.clearSearchQuery();
  }

  /**
   * Function to handle a change in pagination
   * @param e PageEvent instance
   */
  paginate(e: PageEvent) {
    this.#pageSize = e.pageSize;
    this.#skip = e.pageSize * e.pageIndex;
    this.#performSearch();
  }

  #errorEffect = effect(() => {
    if (this.#metadataSearch.searchResults.error()) {
      this.#notify.showError('Error fetching search results.');
    }
  });

  /**
   * This function transforms the checkbox change event to the data required in updateFacet(...) and calls it
   * @param input the Event from the checkbox
   */
  onFacetFilterChanged(input: MatCheckboxChange) {
    const facetData = input.source.name?.split('#');
    if (facetData?.length != 2) {
      return;
    }
    const [facetKey, facetOption] = facetData;
    const newValue = input.checked;
    this.#updateFacets(facetKey, facetOption, newValue);
  }

  /**
   * Turns a FacetFilterSetting object into a string for usage in the url f parameter.
   * This is the inverse operation to the #facetDataFromString function.
   * @param facetData the object to turn into a string
   * @returns the string representation
   */
  #facetDataToString(facetData: FacetFilterSetting): string {
    if (Object.keys(facetData).length === 0) {
      return '';
    }
    let facetStrings = [];
    for (const key in facetData) {
      for (const index in facetData[key]) {
        facetStrings.push(key + ':' + facetData[key][index]);
      }
    }
    return facetStrings.join(';');
  }

  /**
   * Check whether the facet data is different from the last search
   * @returns true if the facet data has changed
   */
  #facetDataChanged(): boolean {
    return (
      this.#facetDataToString(this.facetData()) !==
      this.#facetDataToString(this.#metadataSearch.facets())
    );
  }

  /**
   * Turns a string (as used in the f argument of the url) into a FacetFilterSetting.
   * This is the inverse operation of #facetDataToString.
   * @param input the string to parse
   * @returns The FacetFilterSetting format object
   */
  #facetDataFromString(input: string): FacetFilterSetting {
    if (input.indexOf(':') == -1) {
      return {};
    }
    const filterStrings = input.split(';');
    const ret: FacetFilterSetting = {};
    for (const facet of filterStrings) {
      const [facetName, facetValue] = facet.split(':', 2);
      if (facetValue !== undefined) {
        if (ret[facetName]) {
          ret[facetName].push(facetValue);
        } else {
          ret[facetName] = [facetValue];
        }
      }
    }
    return ret;
  }

  /**
   * Handle the state change of facets filter values.
   * The filter status is tracked in the #facetData object.
   * @param key The key of the facet to update.
   * @param option The option of the facet to update
   * @param newValue The new value of the option of the facet
   */
  #updateFacets(key: string, option: string, newValue: boolean) {
    const facetData = this.facetData();
    if (newValue) {
      // The value has been checked so we need to add it
      if (!facetData[key]) {
        facetData[key] = [option];
      } else {
        if (facetData[key].indexOf(option) == -1) {
          facetData[key].push(option);
        }
      }
    } else {
      // The box has been deselected so we need to remove it
      if (facetData[key]) {
        facetData[key] = facetData[key].filter((item) => item != option);
        if (facetData[key].length == 0) {
          delete facetData[key];
        }
      }
    }
    this.facetData.set({ ...facetData });
  }
}
