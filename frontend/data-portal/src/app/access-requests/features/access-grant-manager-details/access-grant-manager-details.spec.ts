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
import { AccessGrantManagerDetailsComponent } from './access-grant-manager-details';

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

describe('AccessGrantManagerDetailsComponent', () => {
  let result: RenderResult<AccessGrantManagerDetailsComponent>;

  beforeEach(async () => {
    result = await render(AccessGrantManagerDetailsComponent, {
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

  it('should show an error message when the IVA could not be loaded', async () => {
    expect(screen.queryByText(/The IVA could not be loaded/)).toBeNull();

    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivaError.set(new Error('Internal server error'));
    await result.fixture.whenStable();

    expect(screen.getByText(/The IVA could not be loaded/)).toBeVisible();
  });
});
