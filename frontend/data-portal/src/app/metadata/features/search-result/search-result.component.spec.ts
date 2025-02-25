/**
 * Test the dataset expansion panel
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';

import { ActivatedRoute } from '@angular/router';
import { datasetSummary, searchResults } from '@app/../mocks/data';
import {
  DataAccessService,
  MockDataAccessService,
} from '@app/access-requests/services/data-access.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { SearchResultComponent } from './search-result.component';

/**
 * Mock the metadata service as needed for the dataset summary
 */
class MockMetadataService {
  datasetSummary = signal(datasetSummary);
  datasetSummaryError = signal(undefined);
  datasetSummaryIsLoading = signal(false);
}

const fakeActivatedRoute = {
  snapshot: { data: {} },
} as ActivatedRoute;

describe(SearchResultComponent, () => {
  let component: SearchResultComponent;
  let fixture: ComponentFixture<SearchResultComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SearchResultComponent],
      providers: [
        { provide: MetadataService, useClass: MockMetadataService },
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
        { provide: DataAccessService, useClass: MockDataAccessService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SearchResultComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('hit', searchResults.hits.at(0));
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show accession and title', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('GHGAD588887987');
    expect(text).toContain('Test dataset for details');
  });
});
