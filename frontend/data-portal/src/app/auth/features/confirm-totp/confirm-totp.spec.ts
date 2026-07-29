/**
 * Test the confirm TOTP component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuthService } from '@app/auth/services/auth';
import { NotificationService } from '@app/shared/services/notification';
import { ConfirmTotpComponent } from './confirm-totp';

/**
 * Minimal view of the component's protected/private members accessed by these tests.
 */
interface ConfirmTotpComponentInternals {
  verificationError: WritableSignal<boolean>;
  totpForm: { code: () => { value: WritableSignal<string> } };
}

const mockAuthService = {
  verifyTotpCode: vitest.fn(),
  redirectAfterLogin: vitest.fn(),
  lostTotpSetup: vitest.fn(),
};

const mockNotificationService = {
  showSuccess: vitest.fn(),
  showError: vitest.fn(),
};

describe('ConfirmTotpComponent', () => {
  let component: ConfirmTotpComponent;
  let fixture: ComponentFixture<ConfirmTotpComponent>;

  beforeEach(async () => {
    mockAuthService.verifyTotpCode.mockReset();
    mockAuthService.redirectAfterLogin.mockReset();
    mockAuthService.lostTotpSetup.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();

    await TestBed.configureTestingModule({
      imports: [ConfirmTotpComponent],
      providers: [
        { provide: AuthService, useValue: mockAuthService },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmTotpComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  /**
   * Enter the given text into the rendered code input, like a user would.
   * @param text - the raw text to enter
   * @returns the code input element, after the form has settled
   */
  async function enterCode(text: string): Promise<HTMLInputElement> {
    const input: HTMLInputElement = fixture.nativeElement.querySelector('input');
    input.value = text;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
    return input;
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should auto-submit on first complete valid input', async () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    const inputElement = await enterCode('123456');

    expect(inputElement.value).toBe('123456');
    expect(onSubmitSpy).toHaveBeenCalledTimes(1);
  });

  it('should not auto-submit while first input is incomplete', async () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);

    await enterCode('123');

    expect(onSubmitSpy).not.toHaveBeenCalled();
  });

  it('should clear verification error on input', async () => {
    (component as unknown as ConfirmTotpComponentInternals).verificationError.set(true);

    const inputElement = await enterCode('12ab34');

    expect(inputElement.value).toBe('1234');
    expect(
      (component as unknown as ConfirmTotpComponentInternals).totpForm.code().value(),
    ).toBe('1234');
    expect(
      (component as unknown as ConfirmTotpComponentInternals).verificationError(),
    ).toBe(false);
  });

  it('should not auto-submit after a previous submission exists', async () => {
    mockAuthService.verifyTotpCode.mockResolvedValue(true);
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
    mockAuthService.verifyTotpCode.mockResolvedValue(false);
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
});
