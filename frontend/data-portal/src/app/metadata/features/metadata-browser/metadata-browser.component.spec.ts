/**
 * Test the metadata browser component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';

import { ActivatedRoute, RouterModule } from '@angular/router';
import { searchResults } from '@app/../mocks/data';
import { MetadataSearchService } from '../../services/metadata-search.service';
import { SearchResultListComponent } from '../search-result-list/search-result-list.component';
import { MetadataBrowserComponent } from './metadata-browser.component';

/**
 * Mock the metadata service as needed for the metadata browser
 */
class MockMetadataSearchService {
  searchResults = signal(searchResults);
  searchResultsError = signal(undefined);
  searchResultsAreLoading = signal(false);
  loadQueryParameters = () => undefined;
  query = signal('');
  facets = signal({});
}

describe('BrowseComponent', () => {
  let component: MetadataBrowserComponent;
  let fixture: ComponentFixture<MetadataBrowserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataBrowserComponent, NoopAnimationsModule],
      providers: [
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
        RouterModule,
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {},
          },
        },
      ],
    })
      .overrideComponent(MetadataBrowserComponent, {
        remove: { imports: [SearchResultListComponent] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(MetadataBrowserComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show filters', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Dataset Type');
    expect(text).toContain('Test dataset type 1');
  });
});
