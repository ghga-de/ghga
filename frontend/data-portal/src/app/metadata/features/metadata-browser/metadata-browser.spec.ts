/**
 * Test the metadata browser component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute, RouterModule } from '@angular/router';
import { searchResults } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
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
 * Mock SearchResultListComponent as needed for the metadata browser
 */
@Component({
  selector: 'app-metadata-browser-filter',
  template: '<div>Mock Metadata Browser Filter</div>',
})
class MockMetadataBrowserFilterComponent {}

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
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    })
      .overrideComponent(MetadataBrowserComponent, {
        remove: {
          imports: [SearchResultListComponent, MetadataBrowserFilterComponent],
        },
        add: {
          imports: [MockSearchResultListComponent, MockMetadataBrowserFilterComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(MetadataBrowserComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show total datasets', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('26');
  });
});
