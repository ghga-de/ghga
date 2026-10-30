/**
 * Test the Access Grant Manager Details component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { accessGrants, allIvasOfDoe } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { IvaService } from '@app/ivas/services/iva';
import { render, RenderResult, screen } from '@testing-library/angular';
import { AccessGrantManagerDetails } from './access-grant-manager-details';

/**
 * Mock the IVA service as needed by the access grant manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  ivaError = signal<Error | undefined>(undefined);
  userIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: this.ivaError,
  };
}

describe('AccessGrantManagerDetails', () => {
  let result: RenderResult<AccessGrantManagerDetails>;

  beforeEach(async () => {
    result = await render(AccessGrantManagerDetails, {
      providers: [
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: IvaService, useClass: MockIvaService },
      ],
      inputs: { id: accessGrants[0].id },
      routes: [],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Access Grant Detail' }),
    ).toBeVisible();
  });

  it('should label the grantee email as the LS Login email', () => {
    const email = screen.getByText(accessGrants[0].user_email);
    expect(email.closest('p')).toHaveTextContent(
      new RegExp(`LS Login email:\\s*${accessGrants[0].user_email}`),
    );
  });

  it('should show an error message when the IVA could not be loaded', async () => {
    expect(screen.queryByText(/The IVA could not be loaded/)).toBeNull();

    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivaError.set(new Error('Internal server error'));
    await result.fixture.whenStable();

    expect(screen.getByText(/The IVA could not be loaded/)).toBeVisible();
  });
});
