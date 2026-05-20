/**
 * Test the user IVA list component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Iva, IvaState, IvaType } from '@app/ivas/models/iva';

import { IvaService } from '@app/ivas/services/iva';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NotificationService } from '@app/shared/services/notification';
import { of, throwError } from 'rxjs';
import { UserIvaListComponent } from './user-iva-list';

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
  userIvas = { value: () => [], isLoading: () => false, error: () => undefined };
  requestCodeForIva = vitest.fn();
}

describe('UserIvaListComponent', () => {
  let component: UserIvaListComponent;
  let fixture: ComponentFixture<UserIvaListComponent>;
  let ivaService: MockIvaService;

  beforeEach(async () => {
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showWarning.mockReset();
    mockNotificationService.showError.mockReset();
    mockConfirmationService.confirm.mockReset();

    await TestBed.configureTestingModule({
      imports: [UserIvaListComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: ConfirmationService, useValue: mockConfirmationService },
      ],
    }).compileComponents();

    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    fixture = TestBed.createComponent(UserIvaListComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should say that there are no user IVAs', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('You have not yet created any IVAs.');
  });

  it('should show a dedicated message when verification requests are rate limited', () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(throwError(() => ({ status: 429 })));

    component.requestVerification(testIva);

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Too many verification requests today',
    );
  });

  it('should keep the generic error message for non-rate-limit failures', () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(throwError(() => ({ status: 500 })));

    component.requestVerification(testIva);

    expect(mockNotificationService.showError).toHaveBeenCalledWith(
      'Verification request failed',
    );
  });

  it('should request verification after user confirmation', () => {
    mockConfirmationService.confirm.mockImplementation(({ callback }) => {
      callback(true);
    });
    ivaService.requestCodeForIva.mockReturnValue(of(null));

    component.requestVerification(testIva);

    expect(ivaService.requestCodeForIva).toHaveBeenCalledWith(testIva.id, testIva.type);
    expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
      'Verification has been requested',
    );
  });
});
