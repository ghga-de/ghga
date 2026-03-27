/**
 * Tests for the Upload Grant Creation page component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNativeDateAdapter } from '@angular/material/core';
import { ActivatedRoute } from '@angular/router';
import { uploadBoxes } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { UserStatus } from '@app/auth/models/user';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { Iva, IvaState, IvaType } from '@app/ivas/models/iva';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ResearchDataUploadBox } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { screen } from '@testing-library/angular';
import { of, throwError } from 'rxjs';
import { UploadGrantCreationComponent } from './upload-grant-creation';

const testBox = uploadBoxes.boxes[0];

const testUser: DisplayUser = {
  id: 'doe@test.dev',
  ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaad@lifescience-ri.eu',
  name: 'John Doe',
  title: 'Dr.',
  email: 'doe@home.org',
  roles: ['data_steward'],
  status: UserStatus.active,
  registration_date: '2022-06-01T00:00:00',
  displayName: 'Dr. John Doe',
  roleNames: ['Data Steward'],
  sortName: 'Doe, John',
};

const testUser2: DisplayUser = {
  id: 'roe@test.dev',
  ext_id: 'aacaffeecaffeecaffeecaffeecaffeecaffeeaae@lifescience-ri.eu',
  name: 'Jane Roe',
  title: 'Prof.',
  email: 'roe@home.org',
  roles: [],
  status: UserStatus.active,
  registration_date: '2023-01-01T00:00:00',
  displayName: 'Prof. Jane Roe',
  roleNames: [],
  sortName: 'Roe, Jane',
};

const testIvas: Iva[] = [
  {
    id: '783d9682-d5e5-4ce7-9157-9eeb53a1e9ba',
    type: IvaType.Phone,
    value: '+441234567890004',
    changed: '2024-02-01T00:00:00',
    state: IvaState.Verified,
  },
];

const mockNotificationService = { showSuccess: vitest.fn(), showError: vitest.fn() };
const mockNavigationService = { back: vitest.fn() };

/**
 * Minimal mock of UploadBoxService for grant creation tests.
 */
class MockUploadBoxService {
  #uploadBoxValue = signal<ResearchDataUploadBox | undefined>(undefined);
  #uploadBoxError = signal<unknown>(undefined);

  uploadBox = {
    value: this.#uploadBoxValue.asReadonly(),
    error: this.#uploadBoxError.asReadonly(),
  };

  loadUploadBox = vitest.fn();
  createUploadGrant = vitest.fn();

  /**
   * Set the upload box value in the mock resource.
   * @param box - the box to set
   */
  setUploadBox(box: ResearchDataUploadBox | undefined): void {
    this.#uploadBoxValue.set(box);
  }
}

/**
 * Minimal mock of UserService for grant creation tests.
 */
class MockUserService {
  users = {
    value: signal<DisplayUser[]>([]),
    isLoading: signal(false),
  };

  loadUsers = vitest.fn();

  /**
   * Set the users available in the mock resource.
   * @param users - the display users to set
   */
  setUsers(users: DisplayUser[]): void {
    this.users.value.set(users);
  }
}

/**
 * Minimal mock of IvaService for grant creation tests.
 */
class MockIvaService {
  userIvas = {
    value: signal<Iva[]>([]),
    isLoading: signal(false),
    error: signal<unknown>(undefined),
  };

  loadUserIvas = vitest.fn();

  /**
   * Set the IVAs available in the mock resource.
   * @param ivas - the IVAs to set
   */
  setUserIvas(ivas: Iva[]): void {
    this.userIvas.value.set(ivas);
  }
}

describe('UploadGrantCreationComponent', () => {
  let component: UploadGrantCreationComponent;
  let fixture: ComponentFixture<UploadGrantCreationComponent>;
  let uploadBoxService: MockUploadBoxService;
  let userService: MockUserService;
  let ivaService: MockIvaService;

  beforeEach(async () => {
    mockNotificationService.showSuccess.mockReset();
    mockNotificationService.showError.mockReset();
    mockNavigationService.back.mockReset();

    await TestBed.configureTestingModule({
      imports: [UploadGrantCreationComponent],
      providers: [
        provideNativeDateAdapter(),
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: UserService, useClass: MockUserService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: NotificationService, useValue: mockNotificationService },
        { provide: NavigationTrackingService, useValue: mockNavigationService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    userService = TestBed.inject(UserService) as unknown as MockUserService;
    ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;

    fixture = TestBed.createComponent(UploadGrantCreationComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('boxId', testBox.id);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should call loadUsers on init', () => {
    expect(userService.loadUsers).toHaveBeenCalled();
  });

  it('should call loadUploadBox when box is not yet loaded', () => {
    expect(uploadBoxService.loadUploadBox).toHaveBeenCalledWith(testBox.id);
  });

  it('should show the heading', () => {
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'New Upload Grant',
    );
  });

  it('should show the search input before a user is selected', () => {
    expect(
      screen.getByLabelText(/search by name, email or external id/i),
    ).toBeVisible();
  });

  describe('user search and selection', () => {
    beforeEach(async () => {
      userService.setUsers([testUser, testUser2]);
      component.searchQuery.set('john');
      fixture.detectChanges();
      await fixture.whenStable();
    });

    it('should show matching users in the results table', () => {
      expect(screen.getByText('Dr. John Doe')).toBeVisible();
    });

    it('should not show non-matching users', () => {
      expect(screen.queryByText('Prof. Jane Roe')).not.toBeInTheDocument();
    });

    describe('after selecting a user', () => {
      beforeEach(async () => {
        component.selectUser(testUser);
        fixture.detectChanges();
        await fixture.whenStable();
      });

      it('should hide the search input', () => {
        expect(
          screen.queryByLabelText(/search by name, email or external id/i),
        ).not.toBeInTheDocument();
      });

      it('should display the selected user name', () => {
        expect(screen.getByText('Dr. John Doe')).toBeVisible();
      });

      it('should display the selected user email', () => {
        expect(screen.getByText('doe@home.org')).toBeVisible();
      });

      it('should show the IVA selection card', () => {
        expect(screen.getByText(/select an iva/i)).toBeVisible();
      });

      it('should load IVAs for the selected user', () => {
        expect(ivaService.loadUserIvas).toHaveBeenCalledWith(testUser.id);
      });

      describe('after clearing the user', () => {
        beforeEach(async () => {
          component.clearUser();
          fixture.detectChanges();
          await fixture.whenStable();
        });

        it('should show the search input again', () => {
          expect(
            screen.getByLabelText(/search by name, email or external id/i),
          ).toBeVisible();
        });
      });

      describe('after selecting an IVA', () => {
        beforeEach(async () => {
          component.selectedIvaId.set(testIvas[0].id);
          fixture.detectChanges();
          await fixture.whenStable();
        });

        it('should show the validity period card', () => {
          expect(screen.getByText(/validity period/i)).toBeVisible();
        });

        it('should show the submit button', () => {
          expect(
            screen.getByRole('button', { name: /create upload grant/i }),
          ).toBeVisible();
        });
      });
    });
  });

  describe('canSubmit signal', () => {
    it('should be false when no user is selected', () => {
      expect(component.canSubmit()).toBe(false);
    });

    it('should be false when user is selected but IVA selection is not done', () => {
      component.selectedUser.set(testUser);
      expect(component.canSubmit()).toBe(false);
    });

    it('should be true when user is selected and IVA selection is done', () => {
      component.selectedUser.set(testUser);
      component.selectedIvaId.set(testIvas[0].id);
      expect(component.canSubmit()).toBe(true);
    });

    it('should be false while submitting', () => {
      component.selectedUser.set(testUser);
      component.selectedIvaId.set(testIvas[0].id);
      component.isSubmitting.set(true);
      expect(component.canSubmit()).toBe(false);
    });
  });

  describe('submit()', () => {
    beforeEach(() => {
      component.selectedUser.set(testUser);
      component.selectedIvaId.set(testIvas[0].id);
    });

    describe('on success', () => {
      beforeEach(async () => {
        uploadBoxService.createUploadGrant.mockReturnValue(of({ id: 'new-grant-001' }));
        component.submit();
        await fixture.whenStable();
      });

      it('should call createUploadGrant with a payload including the user and box', () => {
        const [payload] = uploadBoxService.createUploadGrant.mock.calls[0];
        expect(payload.user_id).toBe(testUser.id);
        expect(payload.box_id).toBe(testBox.id);
        expect(payload.iva_id).toBe(testIvas[0].id);
      });

      it('should pass the user metadata to createUploadGrant', () => {
        const [, user] = uploadBoxService.createUploadGrant.mock.calls[0];

        expect(user).toEqual(
          expect.objectContaining({
            name: testUser.displayName,
            email: testUser.email,
            title: testUser.title,
          }),
        );
      });

      it('should show a success notification', () => {
        expect(mockNotificationService.showSuccess).toHaveBeenCalledWith(
          'Upload grant created successfully.',
        );
      });

      it('should navigate back to the box detail page', () => {
        expect(mockNavigationService.back).toHaveBeenCalledWith([
          '/upload-box-manager',
          testBox.id,
        ]);
      });
    });

    describe('on error', () => {
      beforeEach(async () => {
        uploadBoxService.createUploadGrant.mockReturnValue(
          throwError(() => new Error('Server error')),
        );
        component.submit();
        await fixture.whenStable();
      });

      it('should show an error notification', () => {
        expect(mockNotificationService.showError).toHaveBeenCalledWith(
          'Failed to create upload grant. Please try again.',
        );
      });

      it('should reset isSubmitting to false', () => {
        expect(component.isSubmitting()).toBe(false);
      });

      it('should not navigate away', () => {
        expect(mockNavigationService.back).not.toHaveBeenCalled();
      });
    });
  });
});
