/**
 * Test the metadata browser component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute, RouterModule } from '@angular/router';
import { searchResults } from '@app/../mocks/data';
import { ConfigService } from '@app/shared/services/config';
import { MetadataSearchService } from '../../services/metadata-search';
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
  searchResults = {
    value: () => searchResults,
    isLoading: () => false,
    error: () => undefined,
  };
  searchResultsAreLoading = signal(false);
  loadQueryParameters = () => undefined;
  query = signal('');
  facets = signal({});
}

describe('MetadataBrowserComponent', () => {
  let component: MetadataBrowserComponent;
  let fixture: ComponentFixture<MetadataBrowserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataBrowserComponent],
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
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
