/**
 * Test the metadata browser filter component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute, provideRouter, Router, RouterModule } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { MetadataSearchService } from '@app/metadata/services/metadata-search';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { searchResults } from 'src/mocks/data';
import { MetadataBrowserFilterComponent } from './metadata-browser-filter';

/**
 * Mock the metadata service as needed for the metadata browser filter
 */
class MockMetadataSearchService {
  searchResultsResource = {
    value: () => searchResults,
    isLoading: () => false,
    error: () => undefined,
  };
  searchResults = () => searchResults;
  isLoading = () => false;
  searchResultsLimit = () => 10;
  searchResultsSkip = () => 0;
  paginated = () => false;
  resetSkip = () => {};
  loadQueryParameters = () => {};
  facets = () => {};
  query = () => undefined;
}
describe('MetadataBrowserFilterComponent', () => {
  let component: MetadataBrowserFilterComponent;
  let fixture: ComponentFixture<MetadataBrowserFilterComponent>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataBrowserFilterComponent],
      providers: [
        RouterModule,
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        { provide: ConfigService, useValue: { massUrl: '' } },
        { provide: MetadataSearchService, useClass: MockMetadataSearchService },
        provideRouter([]),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MetadataBrowserFilterComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should correctly filter by query', async () => {
    const searchInput = screen.getByPlaceholderText('Enter any keyword or ID');
    const routerSpy = vitest.spyOn(router, 'navigate');
    searchInput.focus();
    await userEvent.keyboard('test{Enter}');
    await fixture.whenStable();
    expect(routerSpy).toHaveBeenCalledWith(
      [],
      expect.objectContaining({
        queryParams: { f: undefined, p: undefined, q: 'test', s: undefined },
      }),
    );
  });

  it('should show the correct number of facet expansion panels', () => {
    const buttons = screen.getAllByRole('button');
    const expansionPanels = buttons.filter((x) =>
      x.className.includes('mat-expansion-panel-header'),
    );
    expect(expansionPanels.length).toBe(2);
  });
});
