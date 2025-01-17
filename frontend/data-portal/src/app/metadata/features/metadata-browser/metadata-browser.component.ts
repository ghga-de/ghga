/**
 * Metadata browser
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, effect, inject, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatChipsModule } from '@angular/material/chips';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MetadataSearchService } from '@app/metadata/services/metadataSearch.service';
import { DatasetExpansionPanelComponent } from '../dataset-expansion-panel/dataset-expansion-panel.component';

/**
 * This is the metadata browser component
 */
@Component({
  selector: 'app-metadata-browser',
  imports: [
    MatExpansionModule,
    DatasetExpansionPanelComponent,
    MatCheckboxModule,
    MatPaginatorModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
  ],
  templateUrl: './metadata-browser.component.html',
  styleUrl: './metadata-browser.component.scss',
})
export class MetadataBrowserComponent implements OnInit {
  #metadataSearch = inject(MetadataSearchService);

  #className = 'EmbeddedDataset';
  /**
   * On init, define the default values of the search variables
   */
  ngOnInit(): void {
    this.#metadataSearch.loadQueryParameters(this.#className, 10, 0);
  }

  searchFormControl = new FormControl('');

  #skip = 0;

  #pageEvent!: PageEvent;
  pageSize = 10;
  length = computed(() => this.#metadataSearch.searchResults().count);
  /**
   * Function to handle a change in pagination
   * @param e PageEvent instance
   */
  handlePageEvent(e: PageEvent) {
    this.#pageEvent = e;
    this.pageSize = e.pageSize;
    this.#skip = e.pageSize * e.pageIndex;
    this.#metadataSearch.loadQueryParameters(
      this.#className,
      this.pageSize,
      this.#skip,
    );
  }

  #errorEffect = effect(() => {
    if (this.#metadataSearch.searchResultsError()) {
      console.log('Error fetching search results'); // TODO: show a toast message
    }
  });

  searchResults = this.#metadataSearch.searchResults;
}
