/**
 * Test the user IVA list component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Iva, IvaState, IvaType } from '@app/ivas/models/iva';

import { IvaService } from '@app/ivas/services/iva';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { Notifier } from '@app/shared/services/notification';
import { render, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';
import { UserIvaList } from './user-iva-list';

const mockNotificationService = {
  showSuccess: vitest.fn(),
  showWarning: vitest.fn(),
  showError: vitest.fn(),
};

const mockConfirmationService = {
  confirm: vitest.fn(),
};

const testIva: Iva = {
  id: 'iva-123',
  type: IvaType.Phone,
  value: '+49123456789',
  changed: '2026-01-01T00:00:00.000Z',
  state: IvaState.Unverified,
};

/**
 * Mock the IVA service as needed by the user IVA list component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  reloadUserIvas = vitest.fn();
  ivas = signal<Iva[]>([]);
  userIvas = {
    value: this.ivas.asReadonly(),
    isLoading: () => false,
    error: () => undefined,
  };
  requestCodeForIva = vitest.fn();
}

describe('UserIvaList', () => {
  let component: UserIvaList;
  let fixture: ComponentFixture<UserIvaList>;
  let ivaService: MockIvaService;

  /**
   * Show the given IVA in the list and request its verification via its button.
   * @param iva - the IVA to show and request verification for
   */
  async function clickRequestVerification(iva: Iva): Promise<void> {
    ivaService.ivas.set([iva]);
    await fixture.whenStable();
    await userEvent.click(screen.getByRole('button', { name: /Request verification/ }));
  }

  beforeEach(async () => {
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showWarning.mockReset();
    mockNotificationService.showError.mockReset();
    mockConfirmationService.confirm.mockReset();

    ({ fixture } = await render(UserIvaList, {
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: Notifier, useValue: mockNotificationService },
        { provide: ConfirmationService, useValue: mockConfirmationService },
      ],
    }));
    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should fetch the IVAs again when refreshed', () => {
    component.reload();
    expect(ivaService.reloadUserIvas).toHaveBeenCalledTimes(1);
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should say that there are no user IVAs', () => {
    expect(screen.getByText(/You have not yet created any IVAs\./)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Add an IVA/ })).toBeInTheDocument();
  });

  it('should list the IVAs of the user with their state', async () => {
    ivaService.ivas.set([testIva]);
    await fixture.whenStable();

    expect(screen.queryByText(/You have not yet created any IVAs\./)).toBeNull();
    expect(screen.getByText('SMS: +49123456789')).toBeInTheDocument();
    expect(screen.getByText(/Needs verification/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('should show a dedicated message when verification requests are rate limited', async () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(throwError(() => ({ status: 429 })));

    await clickRequestVerification(testIva);

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Too many verification requests today',
    );
  });

  it('should keep the generic error message for non-rate-limit failures', async () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(throwError(() => ({ status: 500 })));

    await clickRequestVerification(testIva);

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Verification request failed',
    );
  });

  it('should ask for consent before sending an SMS', async () => {
    await clickRequestVerification(testIva);

    expect(mockConfirmationService.confirm).toHaveBeenCalledWith(
      expect.objectContaining({
        title: 'Send verification code by SMS',
        message: expect.stringContaining('you agree to receive this message'),
        confirmText: 'Send SMS',
      }),
    );
    expect(mockConfirmationService.confirm.mock.calls[0][0].message).toContain(
      '+49123456789',
    );
  });

  it('should not ask for SMS consent for other IVA types', async () => {
    await clickRequestVerification({
      ...testIva,
      type: IvaType.InPerson,
      value: 'Heidelberg',
    });

    const options = mockConfirmationService.confirm.mock.calls[0][0];
    expect(options.title).toBe('Request verification of your address');
    expect(options.message).not.toContain('SMS');
    expect(options.confirmText).toBeUndefined();
  });

  it('should request verification after user confirmation', async () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(of(null));

    await clickRequestVerification(testIva);

    expect(ivaService.requestCodeForIva).toHaveBeenCalledWith(testIva.id, testIva.type);
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Verification has been requested',
    );
  });
});
