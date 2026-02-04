/**
 * Unit tests for the account page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { ConfigService } from '@app/shared/services/config';
import { provideHttpCache } from '@ngneat/cashew';
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
  userIvas = { value: () => [], isLoading: () => false, error: () => undefined };
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
});
