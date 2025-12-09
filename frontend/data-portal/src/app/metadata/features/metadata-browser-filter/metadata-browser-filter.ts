/**
 * Metadata browser filter component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject, OnInit, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxChange, MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatAccordion } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { ActivatedRoute, Router } from '@angular/router';
import { FacetFilterSetting } from '@app/metadata/models/facet-filter';
import {
  DEFAULT_PAGE_SIZE,
  DEFAULT_SKIP_VALUE,
  Facet,
} from '@app/metadata/models/search-results';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { FacetExpansionPanelComponent } from '@app/metadata/ui/facet-expansion-panel/facet-expansion-panel';
import { StencilComponent } from '@app/shared/ui/stencil/stencil/stencil';

/**
 * Component for the metadata browser filter
 */
@Component({
  selector: 'app-metadata-browser-filter',
  imports: [
    FacetExpansionPanelComponent,
    MatButtonModule,
    MatCardModule,
    MatCheckboxModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    StencilComponent,
    ReactiveFormsModule,
    MatAccordion,
  ],
  templateUrl: './metadata-browser-filter.html',
})
export class MetadataBrowserFilterComponent implements OnInit {
  #className = 'EmbeddedDataset';

  #route = inject(ActivatedRoute);
  #router = inject(Router);
  #metadataSearch = inject(MetadataSearchService);
  #searchResults = this.#metadataSearch.searchResultsResource;
  #facetResults = computed(() =>
    this.#searchResults.error() ? [] : this.#searchResults.value().facets,
  );
  protected facets = signal<Facet[]>([]);
  readonly isLoading = computed(() => this.#metadataSearch.isLoading);
  pageSize = computed(() => this.#metadataSearch.searchResultsLimit());
  #skip = computed(() => this.#metadataSearch.searchResultsSkip());
  #currentFacet: string | null | undefined;

  protected expandedPanels: { [facetKey: string]: boolean } = {};

  protected facetData = signal<FacetFilterSetting>({});
  protected searchFormValue = signal<string | null>('');
  protected searchTerm = '';
  protected lastSearchQuery = computed(() => this.#metadataSearch.query());
  protected selectedFacets = computed(() => this.#metadataSearch.facets());

  readonly paginated = this.#metadataSearch.paginated;

  protected searchFormControl = new FormControl('');

  protected searchFormGroup = new FormGroup({
    searchTerm: this.searchFormControl,
  });

  protected displayFilters = false;

  protected facetWithSelectedOptions = computed(() =>
    this.facets().map((f) => {
      return {
        ...f,
        expanded: this.expandedPanels[f.key] ?? false,
      };
    }),
  );

  #paginatedEffect = effect(() => {
    this.paginated() ? this.#performSearch() : null;
  });

  #deferredFacetUpdateEffect = effect(() => {
    if (!this.#searchResults.error() && !this.#searchResults.isLoading()) {
      this.#updateFacetDeferred();
    }
  });

  /**
   * Defer the update of the last selected facet options so the user can click multiple
   * options (to perform an OR query)
   */
  #updateFacetDeferred() {
    const currentFacet = this.#currentFacet;
    if (this.facets().length > 0 && currentFacet !== undefined) {
      const facetPanelIsExpanded = this.expandedPanels[currentFacet!] ?? false;
      if (facetPanelIsExpanded) {
        const newFacets = this.#facetResults().map((x) =>
          x.key === currentFacet
            ? (this.facets().find((x) => x.key === currentFacet) ?? x)
            : x,
        );
        this.facets.set(newFacets);
      }
      this.#currentFacet = null;
    } else {
      this.facets.set(this.#facetResults());
    }
  }

  /**
   * On init, define the default values of the search variables
   */
  ngOnInit(): void {
    this.#loadSearchTermsFromRoute();
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
   * Syncs the data between this component and the search service and initiates a new search.
   */
  #performSearch(): void {
    this.#updateMetadataServiceSearchTermsAndRoute();
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
   * Pushes the local filters, search term and page setup to the search service.
   */
  async #updateMetadataServiceSearchTermsAndRoute(): Promise<void> {
    await this.#router.navigate([], {
      relativeTo: this.#route,
      queryParams: {
        s: this.#skip() !== DEFAULT_SKIP_VALUE ? this.#skip() : undefined,
        q: this.searchTerm !== '' ? this.searchTerm : undefined,
        f:
          Object.keys(this.facetData()).length !== 0
            ? encodeURIComponent(this.#facetDataToString(this.facetData()))
            : undefined,
        p: this.pageSize() !== DEFAULT_PAGE_SIZE ? this.pageSize() : undefined,
      },
    });
    this.#loadSearchTermsFromRoute();
  }

  /**
   * This function takes the current URL, determines the query parameters and sets them accordingly in the metadata search service.
   */
  #loadSearchTermsFromRoute(): void {
    const { s, q, f, p } = this.#router.routerState.snapshot.root.queryParams;
    const pageSize = parseInt(p) || DEFAULT_PAGE_SIZE;
    this.searchTerm = q || '';
    if (f) {
      const paramVals = this.#facetDataFromString(decodeURIComponent(f));
      if (paramVals) {
        this.facetData.set(paramVals);
      }
    }
    const skip = parseInt(s) || DEFAULT_SKIP_VALUE;
    this.#metadataSearch.loadQueryParameters(
      this.#className,
      pageSize,
      skip,
      this.searchTerm,
      this.facetData(),
    );
    this.searchFormValue.set(this.searchTerm);
  }

  /**
   * When an expansion panel has been toggled, store its state in the corresponding
   * variable to make sure we keep the previous view after the facets reload
   * @param facetKey The corresponding facet ID string of the expansion panel
   * @param expanded A boolean stating whether the panel is expanded or not
   */
  onExpansionPanelChange(facetKey: string, expanded: boolean) {
    this.expandedPanels[facetKey] = expanded;
  }

  /**
   * Sets the parameters for the search and triggers it in the metadataSearch Service
   * @param event we need to stop the event from propagating
   */
  protected submit(event: MouseEvent | SubmitEvent | Event): void {
    event.preventDefault();
    const searchTerm = this.searchFormValue() || '';
    if (searchTerm !== this.searchTerm || this.#facetDataChanged()) {
      this.searchTerm = searchTerm;
      this.#metadataSearch.resetSkip();
      this.facets.set([]);
      this.#currentFacet = undefined;
      this.#performSearch();
    }
  }

  /**
   * Handles the click event on a facet filter that was active in the last search (as shown above the search results)
   * @param optionToRemove The facet name and option to remove.
   */
  protected removeOption(optionToRemove: string): void {
    const facetToRemoveSplit = optionToRemove.split('#');
    if (facetToRemoveSplit.length !== 2) return;
    this.#updateFacets(facetToRemoveSplit[0], facetToRemoveSplit[1], false);
    this.#metadataSearch.resetSkip();
    this.facets.set([]);
    this.#currentFacet = undefined;
    this.#performSearch();
  }

  /**
   * Resets the search query and triggers a reload of the results.
   */
  protected clearSearchQuery(): void {
    if (this.searchTerm !== '' || this.searchFormValue() || this.#facetDataChanged()) {
      this.searchTerm = '';
      this.searchFormValue.set('');
      this.#metadataSearch.resetSkip();
      this.facets.set([]);
      this.#currentFacet = undefined;
      this.#performSearch();
    }
  }

  /**
   * Clears the search field input and triggers a result update
   * @param event we need to stop the event from propagating
   */
  protected clear(event: MouseEvent): void {
    event.preventDefault();
    this.facetData.set({});
    this.clearSearchQuery();
  }

  /**
   * Handle the state change of facets filter values.
   * The filter status is tracked in the #facetData object.
   * @param key The key of the facet to update.
   * @param option The option of the facet to update
   * @param newValue The new value of the option of the facet
   * @returns Whether the facets should be reloaded (because all options were removed)
   */
  #updateFacets(key: string, option: string, newValue: boolean): boolean {
    let updateFacets = false;
    const facetData = this.facetData();
    if (newValue) {
      // The value has been checked so we need to add it
      if (!facetData[key]) {
        facetData[key] = [option];
      } else {
        if (facetData[key].indexOf(option) === -1) {
          facetData[key].push(option);
        }
      }
    } else {
      // The box has been deselected so we need to remove it
      if (facetData[key]) {
        facetData[key] = facetData[key].filter((item) => item !== option);
        if (facetData[key].length === 0) {
          delete facetData[key];
          updateFacets = true;
        }
      }
    }
    this.facetData.set({ ...facetData });
    this.#metadataSearch.resetSkip();
    return updateFacets;
  }

  /**
   * This function transforms the checkbox change event to the data required in updateFacet(...) and calls it
   * @param input the Event from the checkbox
   */
  protected onOptionSelected(input: MatCheckboxChange) {
    const facetData = input.source.name?.split('#');
    if (facetData?.length != 2) {
      return;
    }
    const [facetKey, facetOption] = facetData;
    const newValue = input.checked;
    const updateFacets = this.#updateFacets(facetKey, facetOption, newValue);
    if (updateFacets) {
      this.#currentFacet = undefined;
      this.facets.set([]);
    } else {
      this.#currentFacet = facetKey;
    }
    this.#performSearch();
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
}
