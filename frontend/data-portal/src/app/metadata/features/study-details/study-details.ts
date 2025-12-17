/**
 * Study details component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { httpResource } from '@angular/common/http';
import { Component, computed, effect, inject, input, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { Hit, SearchResults } from '@app/metadata/models/search-results';
import { MetadataService } from '@app/metadata/services/metadata';
import { ConfigService } from '@app/shared/services/config';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';

const MAX_DATASETS = 100;

/**
 * Component for the study page
 */
@Component({
  selector: 'app-study-details',
  imports: [
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
    MatTableModule,
    ExternalLinkDirective,
    RouterLink,
  ],
  templateUrl: './study-details.html',
  providers: [MetadataService],
})
export class StudyDetailsComponent implements OnInit {
  #metadataService = inject(MetadataService);
  #location = inject(NavigationTrackingService);
  #study = this.#metadataService.study;
  #config = inject(ConfigService);
  #massUrl = this.#config.massUrl;
  #rtsUrl = this.#config.rtsUrl;

  id = input.required<string>();
  source = new MatTableDataSource<Hit>([]);
  studyDetails = this.#study;

  metadataDownloadUrl = computed(() => `${this.#rtsUrl}/studies/${this.id()}`);

  /**
   * The list of datasets queried via mass.
   */
  #datasetsResource = httpResource<SearchResults>(() => {
    return (
      `${this.#massUrl}/search?class_name=EmbeddedDataset` +
      `&filter_by=study.accession&value=${this.id()}&limit=${MAX_DATASETS}`
    );
  }).asReadonly();

  datasets = computed(() =>
    this.#datasetsResource.hasValue()
      ? this.#datasetsResource.value()
      : { hits: [], total: 0 },
  );
  datasetsLoading = computed(() => this.#datasetsResource.isLoading());
  datasetsError = computed(() => this.#datasetsResource.error());

  #updateSourceEffect = effect(() => (this.source.data = this.datasets().hits));

  /**
   * Called on component initialization
   */
  ngOnInit() {
    this.#metadataService.loadStudy(this.id());
  }

  /**
   * Navigate back to the previous page or the browse page
   */
  goBack(): void {
    setTimeout(() => {
      this.#location.back(['/browse']);
    });
  }
}
