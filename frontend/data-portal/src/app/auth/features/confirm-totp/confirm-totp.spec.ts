/**
 * Test the confirm TOTP component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { WritableSignal } from '@angular/core';
import { ComponentFixture } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AuthService } from '@app/auth/services/auth';
import { Notifier } from '@app/shared/services/notification';
import { fireEvent, render, screen } from '@testing-library/angular';
import { ConfirmTotp } from './confirm-totp';

/**
 * Minimal view of the component's protected/private members accessed by these tests.
 */
interface ConfirmTotpComponentInternals {
  verificationError: WritableSignal<boolean>;
  totpForm: { code: () => { value: WritableSignal<string> } };
}

const ERROR_TEXT = 'The submitted authentication code is invalid.';

const mockAuthService = {
  verifyTotpCode: vitest.fn(),
  redirectAfterLogin: vitest.fn(),
  lostTotpSetup: vitest.fn(),
  showAccountDisabled: vitest.fn(),
};

const mockRouter = { navigate: vitest.fn() };

const mockNotificationService = {
  showSuccess: vitest.fn(),
  showError: vitest.fn(),
};

describe('ConfirmTotp', () => {
  let component: ConfirmTotp;
  let fixture: ComponentFixture<ConfirmTotp>;

  beforeEach(async () => {
    mockAuthService.verifyTotpCode.mockReset();
    mockAuthService.redirectAfterLogin.mockReset();
    mockAuthService.lostTotpSetup.mockReset();
    mockAuthService.showAccountDisabled.mockReset();
    mockRouter.navigate.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();

    ({ fixture } = await render(ConfirmTotp, {
      providers: [
        { provide: AuthService, useValue: mockAuthService },
        { provide: Notifier, useValue: mockNotificationService },
        { provide: Router, useValue: mockRouter },
      ],
    }));
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  /**
   * Enter the given text into the rendered code input, like a user would.
   * @param text - the raw text to enter
   * @returns the code input element, after the form has settled
   */
  async function enterCode(text: string): Promise<HTMLInputElement> {
    const input = screen.getByRole<HTMLInputElement>('textbox', {
      name: 'Authentication code',
    });
    fireEvent.input(input, { target: { value: text } });
    await fixture.whenStable();
    return input;
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should render the code input with a disabled submit button', () => {
    expect(
      screen.getByRole('heading', { name: 'Two-factor authentication' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Authentication code' })).toHaveValue(
      '',
    );
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
    expect(screen.queryByText(ERROR_TEXT)).toBeNull();
  });

  it('should auto-submit on first complete valid input', async () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    const inputElement = await enterCode('123456');

    expect(inputElement).toHaveValue('123456');
    expect(onSubmitSpy).toHaveBeenCalledTimes(1);
  });

  it('should not auto-submit while first input is incomplete', async () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    await enterCode('123');

    expect(onSubmitSpy).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  });

  it('should not show a rejected character', async () => {
    await enterCode('123');
    const inputElement = await enterCode('123a');

    expect(inputElement).toHaveValue('123');
  });

  it('should clear verification error on input', async () => {
    (component as unknown as ConfirmTotpComponentInternals).verificationError.set(true);
    await fixture.whenStable();
    expect(screen.getByText(ERROR_TEXT)).toBeInTheDocument();

    const inputElement = await enterCode('12ab34');

    expect(inputElement).toHaveValue('1234');
    expect(
      (component as unknown as ConfirmTotpComponentInternals).totpForm.code().value(),
    ).toBe('1234');
    expect(
      (component as unknown as ConfirmTotpComponentInternals).verificationError(),
    ).toBe(false);
    expect(screen.queryByText(ERROR_TEXT)).toBeNull();
  });

  it('should redirect after a successful verification', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue('verified');

    await enterCode('123456');

    expect(mockAuthService.verifyTotpCode).toHaveBeenCalledWith('123456');
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Successfully authenticated.',
    );
    expect(mockAuthService.redirectAfterLogin).toHaveBeenCalledTimes(1);
  });

  it('should not auto-submit after a previous submission exists', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue('verified');
    (component as unknown as ConfirmTotpComponentInternals).totpForm
      .code()
      .value.set('123456');
    await component.onSubmit();
    expect(mockAuthService.verifyTotpCode).toHaveBeenCalledTimes(1);

    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    await enterCode('654321');

    expect(onSubmitSpy).not.toHaveBeenCalled();
  });

  it('should block re-submitting the same code after a failed attempt', async () => {
    vitest.useFakeTimers();
    mockAuthService.verifyTotpCode.mockResolvedValue('invalid');
    (component as unknown as ConfirmTotpComponentInternals).totpForm
      .code()
      .value.set('123456');

    const firstSubmit = component.onSubmit();
    await vitest.advanceTimersByTimeAsync(2500);
    await firstSubmit;

    await component.onSubmit();

    expect(mockAuthService.verifyTotpCode).toHaveBeenCalledTimes(1);
    vitest.useRealTimers();
  });

  it('should show the error and disable the submit button after a failed attempt', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue('invalid');

    await enterCode('123456');

    expect(await screen.findByText(ERROR_TEXT)).toBeInTheDocument();
    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Failed to authenticate.',
    );
    expect(screen.getByRole('button', { name: 'Submit' })).toBeDisabled();
  });

  it('should tell a disabled user and leave the page', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue('disabled');

    await enterCode('123456');

    expect(mockAuthService.showAccountDisabled).toHaveBeenCalledTimes(1);
    expect(mockNotificationService.showError).not.toHaveBeenCalled();
    expect(component.allowNavigation).toBe(true);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/']);
    expect(screen.queryByText(ERROR_TEXT)).toBeNull();
  });

  it('should ask a locked user to log in again and leave the page', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue('locked');

    await enterCode('123456');

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Too many failed attempts, please log in again.',
    );
    expect(mockAuthService.showAccountDisabled).not.toHaveBeenCalled();
    expect(component.allowNavigation).toBe(true);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/']);
  });

  it('should request a new setup when the token was lost', () => {
    fireEvent.click(screen.getByRole('button', { name: 'Get new 2FA setup' }));

    expect(mockAuthService.lostTotpSetup).toHaveBeenCalledTimes(1);
    expect(component.allowNavigation).toBe(true);
  });
});
