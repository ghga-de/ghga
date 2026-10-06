/**
 * Test the dataset expansion panel
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { datasetSummary, searchResults } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { MetadataService } from '@app/metadata/services/metadata';
import { SearchResultComponent } from './search-result';

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
 * Mock the IVA service as needed by the dynamic access request button
 */
class MockIvaService {
  userIvas = { error: signal(undefined), value: signal([]) };
  loadUserIvas = () => undefined;
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
  loadDatasetSummary = vitest.fn();
}

describe(SearchResultComponent, () => {
  let result: RenderResult<SearchResultComponent>;

  beforeEach(async () => {
    result = await render(SearchResultComponent, {
      inputs: { hit: searchResults.hits.at(0)! },
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: IvaService, useClass: MockIvaService },
      ],
      configureTestBed: (testBed) =>
        testBed.overrideComponent(SearchResultComponent, {
          set: {
            providers: [{ provide: MetadataService, useClass: MockMetadataService }],
          },
        }),
      routes: [],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show accession and title', () => {
    const header = screen.getByRole('button', { name: /GHGAD12345678901234/ });
    expect(header).toHaveTextContent('GHGAD12345678901234');
    expect(header).toHaveTextContent('Test dataset for details');
  });

  it('should load the dataset summary when opened', async () => {
    const header = screen.getByRole('button', { name: /GHGAD12345678901234/ });
    await userEvent.click(header);
    await result.fixture.whenStable();
    expect(header).toHaveAttribute('aria-expanded', 'true');
    const metadata = result.debugElement.injector.get(MetadataService);
    expect(metadata.loadDatasetSummary).toHaveBeenCalledWith('GHGAD12345678901234');
  });
});
