/**
 * Test the IVA verification dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { IvaService } from '@app/ivas/services/iva';
import { Notifier } from '@app/shared/services/notification';
import { fireEvent, render, screen, waitFor } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { of, throwError } from 'rxjs';
import { VerificationDialog } from './verification-dialog';

/**
 * Shape of the private members of VerificationDialog that the tests
 * need to access. Used to type the `as unknown as ...` casts below.
 */
interface VerificationDialogInternals {
  verificationError: WritableSignal<boolean>;
  codeForm: { code: () => { value: WritableSignal<string> } };
}

const ERROR_TEXT = 'Verification failed. Please try again.';

const mockDialogRef = {
  close: vitest.fn(),
};

const mockNotificationService = {
  showSuccess: vitest.fn(),
  showError: vitest.fn(),
};

/**
 * Minimal IVA service mock for verification dialog tests.
 */
class MockIvaService {
  validateCodeForIva = vitest.fn();
}

describe('VerificationDialog', () => {
  let component: VerificationDialog;
  let fixture: ComponentFixture<VerificationDialog>;
  let ivaService: MockIvaService;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();

    ({ fixture } = await render(VerificationDialog, {
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: { id: 'iva-123', address: 'SMS: 123/456' },
        },
        { provide: IvaService, useClass: MockIvaService },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: Notifier, useValue: mockNotificationService },
      ],
    }));
    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    vitest.useRealTimers();
  });

  /**
   * Enter the given text into the rendered code input, like a user would.
   * @param text - the raw text to enter
   * @returns the code input element, after the form has settled
   */
  async function enterCode(text: string): Promise<HTMLInputElement> {
    const input = screen.getByRole<HTMLInputElement>('textbox', {
      name: 'Verification code',
    });
    fireEvent.input(input, { target: { value: text } });
    await fixture.whenStable();
    return input;
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should sanitize input and auto-submit only on the first attempt', async () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    const inputElement = await enterCode('ab-12!c3');

    expect(inputElement).toHaveValue('AB12C3');
    expect(
      (component as unknown as VerificationDialogInternals).codeForm.code().value(),
    ).toBe('AB12C3');
    expect(onSubmitSpy).toHaveBeenCalledTimes(1);
  });

  it('should clear verification error when user types', async () => {
    (component as unknown as VerificationDialogInternals).verificationError.set(true);

    await enterCode('abc12');

    expect(
      (component as unknown as VerificationDialogInternals).verificationError(),
    ).toBe(false);
  });

  it('should block resubmission of the same code after a failed attempt', async () => {
    vitest.useFakeTimers();
    ivaService.validateCodeForIva.mockReturnValue(throwError(() => ({ status: 403 })));
    (component as unknown as VerificationDialogInternals).codeForm
      .code()
      .value.set('ABC123');

    const firstSubmit = component.onSubmit();
    await vitest.advanceTimersByTimeAsync(2500);
    await firstSubmit;

    await component.onSubmit();

    expect(ivaService.validateCodeForIva).toHaveBeenCalledTimes(1);
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'The entered verification code was invalid. Please enter the submitted code correctly.',
    );
  });

  it('should not auto-submit after a previous submission exists', async () => {
    ivaService.validateCodeForIva.mockReturnValue(of(null));
    (component as unknown as VerificationDialogInternals).codeForm
      .code()
      .value.set('ABC123');
    await component.onSubmit();
    expect(ivaService.validateCodeForIva).toHaveBeenCalledTimes(1);

    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    await enterCode('DEF456');

    expect(onSubmitSpy).not.toHaveBeenCalled();
  });

  it('should render form with novalidate and hide error before failure', async () => {
    await fixture.whenStable();
    const formElement = screen
      .getByRole('textbox', { name: 'Verification code' })
      .closest('form');

    expect(formElement).toHaveAttribute('novalidate');
    expect(screen.queryByText(ERROR_TEXT)).toBeNull();
  });

  it('should show inline error after a failed submission', async () => {
    (component as unknown as VerificationDialogInternals).verificationError.set(true);
    await fixture.whenStable();

    expect(screen.getByText(ERROR_TEXT)).toBeInTheDocument();
  });

  it('should show the address and close the dialog on cancel', async () => {
    expect(
      screen.getByRole('heading', { name: 'IVA verification' }),
    ).toBeInTheDocument();
    expect(screen.getByText('SMS: 123/456')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();

    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(mockDialogRef.close).toHaveBeenCalledWith(undefined);
  });

  it('should close the dialog after a successful verification', async () => {
    ivaService.validateCodeForIva.mockReturnValue(of(null));

    await enterCode('abc123');

    expect(ivaService.validateCodeForIva).toHaveBeenCalledWith('iva-123', 'ABC123');
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Verification was successful',
    );
    await waitFor(() => expect(mockDialogRef.close).toHaveBeenCalledWith(true));
  });

  it('should show expired request error for status 410', async () => {
    ivaService.validateCodeForIva.mockReturnValue(throwError(() => ({ status: 410 })));

    const result = await component.submitVerificationCode('iva-123', 'ABC123');

    expect(result).toBe(false);
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'The verification request has expired. IVA has been reverted to unverified.',
    );
  });

  it('should show rate limit error for status 429', async () => {
    ivaService.validateCodeForIva.mockReturnValue(throwError(() => ({ status: 429 })));

    const result = await component.submitVerificationCode('iva-123', 'ABC123');

    expect(result).toBe(false);
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Too many attempts at entering a code. IVA has been reverted to unverified.',
    );
  });
});
