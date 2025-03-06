/**
 *  Test  displaying search results in a list.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { searchResults } from '@app/../mocks/data';
import { MetadataSearchService } from '@app/metadata/services/metadata-search.service';
import { SearchResultComponent } from '../search-result/search-result.component';
import { SearchResultListComponent } from './search-result-list.component';

/**
 * Mock the metadata service as needed for the results list
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

describe('SearchResultListComponent', () => {
  let component: SearchResultListComponent;
  let fixture: ComponentFixture<SearchResultListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SearchResultListComponent, NoopAnimationsModule],
      providers: [
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
      ],
    })
      .overrideComponent(SearchResultListComponent, {
        remove: { imports: [SearchResultComponent] },
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
