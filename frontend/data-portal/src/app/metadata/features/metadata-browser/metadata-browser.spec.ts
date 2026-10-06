/**
 * Test the metadata browser component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { render, RenderResult, screen } from '@testing-library/angular';

import { searchResults } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';
import { MetadataSearchService } from '../../services/metadata-search';
import { MetadataBrowserFilterComponent } from '../metadata-browser-filter/metadata-browser-filter';
import { SearchResultListComponent } from '../search-result-list/search-result-list';
import { MetadataBrowserComponent } from './metadata-browser';

/**
 * Mock the config service as needed for the metadata browser
 */
class MockConfigService {
  maxFacetOptions = 5;
}

/**
 * Mock the metadata service as needed for the metadata browser
 */
class MockMetadataSearchService {
  searchResults = () => searchResults;
  isLoading = () => false;
  error = () => undefined;
  loadQueryParameters = () => undefined;
  query = () => '';
  facets = () => [];
}

/**
 * Mock SearchResultListComponent as needed for the metadata browser
 */
@Component({
  selector: 'app-search-result-list',
  template: '<div>Mock Search Result List</div>',
})
class MockSearchResultListComponent {}

/**
 * Mock MetadataBrowserFilterComponent as needed for the metadata browser
 */
@Component({
  selector: 'app-metadata-browser-filter',
  template: '<div>Mock Metadata Browser Filter</div>',
})
class MockMetadataBrowserFilterComponent {}

describe('MetadataBrowserComponent', () => {
  let result: RenderResult<MetadataBrowserComponent>;

  beforeEach(async () => {
    result = await render(MetadataBrowserComponent, {
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
      ],
      importOverrides: [
        { replace: SearchResultListComponent, with: MockSearchResultListComponent },
        {
          replace: MetadataBrowserFilterComponent,
          with: MockMetadataBrowserFilterComponent,
        },
      ],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the heading', () => {
    expect(
      screen.getByRole('heading', { level: 1, name: 'Browse Data' }),
    ).toBeInTheDocument();
  });

  it('should show total datasets', () => {
    expect(screen.getByText('Total Datasets:')).toBeInTheDocument();
    expect(screen.getByText('26')).toBeInTheDocument();
  });

  it('should show the filter and the search result list', () => {
    expect(screen.getByText('Mock Metadata Browser Filter')).toBeInTheDocument();
    expect(screen.getByText('Mock Search Result List')).toBeInTheDocument();
  });
});
