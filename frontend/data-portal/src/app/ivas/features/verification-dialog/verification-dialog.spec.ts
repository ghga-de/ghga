/**
 * Test the IVA verification dialog component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { By } from '@angular/platform-browser';
import { IvaService } from '@app/ivas/services/iva';
import { NotificationService } from '@app/shared/services/notification';
import { of, throwError } from 'rxjs';
import { VerificationDialogComponent } from './verification-dialog';

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

describe('VerificationDialogComponent', () => {
  let component: VerificationDialogComponent;
  let fixture: ComponentFixture<VerificationDialogComponent>;
  let ivaService: MockIvaService;

  beforeEach(async () => {
    mockDialogRef.close.mockReset();
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();

    await TestBed.configureTestingModule({
      imports: [VerificationDialogComponent],
      providers: [
        {
          provide: MAT_DIALOG_DATA,
          useValue: { id: 'iva-123', address: 'SMS: 123/456' },
        },
        { provide: IvaService, useClass: MockIvaService },
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: NotificationService, useValue: mockNotificationService },
      ],
    }).compileComponents();

    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    fixture = TestBed.createComponent(VerificationDialogComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  afterEach(() => {
    vitest.useRealTimers();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should sanitize input and auto-submit only on the first attempt', () => {
    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);
    const inputElement = document.createElement('input');
    inputElement.value = 'ab-12!c3';

    component.onInput({ target: inputElement } as unknown as Event);

    expect(inputElement.value).toBe('AB12C3');
    expect(onSubmitSpy).toHaveBeenCalledTimes(1);
  });

  it('should clear verification error when user types', () => {
    const inputElement = document.createElement('input');
    inputElement.value = 'abc12';
    (component as any).verificationError.set(true);

    component.onInput({ target: inputElement } as unknown as Event);

    expect((component as any).verificationError()).toBe(false);
  });

  it('should block resubmission of the same code after a failed attempt', async () => {
    vitest.useFakeTimers();
    ivaService.validateCodeForIva.mockReturnValue(throwError(() => ({ status: 403 })));
    (component as any).codeForm.code().value.set('ABC123');

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
    (component as any).codeForm.code().value.set('ABC123');
    await component.onSubmit();
    expect(ivaService.validateCodeForIva).toHaveBeenCalledTimes(1);

    const onSubmitSpy = vitest
      .spyOn(component, 'onSubmit')
      .mockResolvedValue(undefined);
    const inputElement = document.createElement('input');
    inputElement.value = 'DEF456';

    component.onInput({ target: inputElement } as unknown as Event);

    expect(onSubmitSpy).not.toHaveBeenCalled();
  });

  it('should render form with novalidate and hide error before failure', () => {
    fixture.detectChanges();
    const formElement = fixture.debugElement.query(By.css('form')).nativeElement;

    expect(formElement.hasAttribute('novalidate')).toBe(true);
    expect(fixture.debugElement.query(By.css('mat-error'))).toBeNull();
  });

  it('should show inline error after a failed submission', () => {
    (component as any).verificationError.set(true);
    fixture.detectChanges();

    expect(fixture.debugElement.query(By.css('mat-error'))).not.toBeNull();
  });
});
