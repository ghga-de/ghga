/**
 * Test the dataset summary component
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
import { DatasetSummaryComponent } from './dataset-summary';

/**
 * Mock the auth service as needed for the Dataset Summary Component
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

describe('DatasetSummaryComponent', () => {
  let result: RenderResult<DatasetSummaryComponent>;

  beforeEach(async () => {
    result = await render(DatasetSummaryComponent, {
      inputs: { hit: searchResults.hits.at(0)!, summary: datasetSummary },
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: IvaService, useClass: MockIvaService },
      ],
      routes: [],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show accession and title', () => {
    expect(screen.getByText('GHGAD12345678901234')).toBeInTheDocument();
    expect(screen.getByText('Test dataset for details')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^EGA Dataset/ })).toHaveAttribute(
      'href',
      'https://ega-archive.org/datasets/EGAD12345678901',
    );
    expect(screen.getByText('EGA ID:')).toBeInTheDocument();
  });

  it('should not show ega details and button for empty string ega accession', async () => {
    await result.rerender({
      inputs: { hit: searchResults.hits.at(3)! },
      partialUpdate: true,
    });

    expect(screen.queryByRole('link', { name: /^EGA Dataset/ })).toBeNull();
    expect(screen.queryByText('EGA ID:')).toBeNull();
  });

  it('should not show ega details and button for undefined ega accession', async () => {
    await result.rerender({
      inputs: { hit: searchResults.hits.at(4)! },
      partialUpdate: true,
    });

    expect(screen.queryByRole('link', { name: /^EGA Dataset/ })).toBeNull();
    expect(screen.queryByText('EGA ID:')).toBeNull();
  });
});
