/**
 *  Test  displaying search results in a list.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { render, RenderResult, screen } from '@testing-library/angular';

import { datasetSummary, searchResults } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { MetadataService } from '@app/metadata/services/metadata';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { SearchResult } from '../search-result/search-result';
import { SearchResultList } from './search-result-list';

/**
 * Mock the metadata service as needed for the search result list
 */
class MockMetadataSearchService {
  searchResults = () => searchResults;
  isLoading = () => false;
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

/**
 * Mock the IVA service as needed by the dynamic access request button
 */
class MockIvaService {
  userIvas = { error: signal(undefined), value: signal([]) };
  loadUserIvas = () => undefined;
}

describe('SearchResultList', () => {
  let result: RenderResult<SearchResultList>;

  beforeEach(async () => {
    result = await render(SearchResultList, {
      providers: [
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
        { provide: IvaService, useClass: MockIvaService },
      ],
      childComponentOverrides: [
        {
          component: SearchResult,
          providers: [
            { provide: AuthService, useClass: MockAuthService },
            { provide: AccessRequestService, useClass: MockAccessRequestService },
            { provide: MetadataService, useClass: MockMetadataService },
          ],
        },
      ],
      routes: [],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show a panel for every search result', () => {
    for (const hit of searchResults.hits) {
      const header = screen.getByRole('button', { name: new RegExp(`^${hit.id_}`) });
      expect(header).toHaveAttribute('aria-expanded', 'false');
    }
  });

  it('should show the paginator with the total number of results', () => {
    expect(screen.getByText('1 – 10 of 26')).toBeInTheDocument();
  });
});
