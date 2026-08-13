/**
 * Unit tests for the account page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { ConfigService } from '@app/shared/services/config';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { provideHttpCache } from '@ngneat/cashew';
import { screen } from '@testing-library/angular';
import { AccountComponent } from './account';

/**
 * Mock the auth service as needed for the account component
 */
class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
  user = () => null;
}

/**
 * Mock the IVA service as needed by the account component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  reloadUserIvas = vitest.fn();
  userIvas = { value: () => [], isLoading: () => false, error: () => undefined };
}

/**
 * Mock the upload box service as needed by the account component
 */
class MockUploadBoxService {
  userGrants = {
    value: signal([]),
    error: signal(undefined),
    isLoading: signal(false),
    reload: () => undefined,
  };
  loadUserGrants = () => undefined;
  reloadUserGrants = vitest.fn();
}

const MockConfigService = {
  auth_url: '/test/auth',
};

describe('AccountComponent', () => {
  let component: AccountComponent;
  let fixture: ComponentFixture<AccountComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccountComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: ConfigService, useValue: MockConfigService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        provideHttpClient(),
        provideHttpCache(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AccountComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  // The refresh buttons sit in the card headers, next to the section headings,
  // but the fetching itself belongs to the list inside each card. Bound via
  // template reference variables, this pairing is easy to get wrong, so every
  // button is checked to reach the list it belongs to.
  const refreshButtons: {
    label: string;
    reload: () => ReturnType<typeof vitest.fn>;
  }[] = [
    {
      label: 'Refresh your IVAs',
      reload: () =>
        (TestBed.inject(IvaService) as unknown as MockIvaService).reloadUserIvas,
    },
    {
      label: 'Refresh your dataset access',
      reload: () =>
        vitest.spyOn(TestBed.inject(AccessRequestService), 'reloadUserAccessGrants'),
    },
    {
      label: 'Refresh your pending access requests',
      reload: () =>
        vitest.spyOn(TestBed.inject(AccessRequestService), 'reloadUserAccessRequests'),
    },
    {
      label: 'Refresh your Research Data Upload Boxes',
      reload: () =>
        (TestBed.inject(UploadBoxService) as unknown as MockUploadBoxService)
          .reloadUserGrants,
    },
  ];

  for (const { label, reload } of refreshButtons) {
    it(`should refresh the matching section via "${label}"`, () => {
      const spy = reload();
      const callsBefore = spy.mock.calls.length;
      screen.getByRole('button', { name: label }).click();
      expect(spy.mock.calls.length).toBe(callsBefore + 1);
    });
  }
});
