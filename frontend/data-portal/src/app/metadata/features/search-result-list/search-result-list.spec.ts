/**
 *  Test  displaying search results in a list.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { datasetSummary, searchResults } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { MetadataService } from '@app/metadata/services/metadata';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { fakeActivatedRoute } from 'src/mocks/route';
import { SearchResultComponent } from '../search-result/search-result';
import { SearchResultListComponent } from './search-result-list';

/**
 * Mock the metadata service as needed for the search result list
 */
class MockMetadataSearchService {
  searchResults = {
    value: () => searchResults,
    isLoading: () => false,
    error: () => undefined,
  };
  searchResultsLimit = () => 10;
  searchResultsSkip = () => 0;
}

/**
 * Mock the metadata service as needed for the search result list
 */
class MockMetadataService {
  datasetSummary = {
    value: () => datasetSummary,
    isLoading: () => false,
    error: () => undefined,
  };
}

/**
 * Mock the auth service as needed for the search result list
 */
class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

describe('SearchResultListComponent', () => {
  let component: SearchResultListComponent;
  let fixture: ComponentFixture<SearchResultListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SearchResultListComponent],
      providers: [
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
      ],
    })
      .overrideComponent(SearchResultComponent, {
        set: {
          providers: [
            { provide: ActivatedRoute, useValue: fakeActivatedRoute },
            { provide: AuthService, useClass: MockAuthService },
            { provide: AccessRequestService, useClass: MockAccessRequestService },
            { provide: MetadataService, useClass: MockMetadataService },
          ],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SearchResultListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
