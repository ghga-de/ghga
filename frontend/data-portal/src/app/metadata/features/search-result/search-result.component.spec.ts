/**
 * Test the dataset expansion panel
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { datasetSummary, searchResults } from '@app/../mocks/data';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AuthService } from '@app/auth/services/auth.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { SearchResultComponent } from './search-result.component';

const fakeActivatedRoute = {
  snapshot: { data: {} },
} as ActivatedRoute;

/**
 * Mock the auth service as needed for the search result component
 */
class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

/**
 * Mock the metadata service as needed for the search result component
 */
class MockMetadataService {
  datasetSummary = {
    value: () => datasetSummary,
    isLoading: () => false,
    error: () => undefined,
  };
}

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
        { provide: AuthService, useClass: MockAuthService },
        { provide: MetadataService, useClass: MockMetadataService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    })
      .overrideComponent(SearchResultComponent, {
        set: {
          providers: [{ provide: MetadataService, useClass: MockMetadataService }],
        },
      })
      .compileComponents();

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
    expect(text).toContain('GHGAD12345678901234');
    expect(text).toContain('Test dataset for details');
  });
});
