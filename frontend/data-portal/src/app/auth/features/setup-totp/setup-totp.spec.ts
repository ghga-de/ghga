/**
 * Test the TOTP token setup component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthService } from '@app/auth/services/auth';
import { SetupTotpComponent } from './setup-totp';

/**
 * Mock the auth service as needed for the setup TOTP component
 */
class MockAuthService {
  /**
   * Pretend to have determined the login state
   * @returns always false
   */
  isUndetermined = () => false;

  /**
   * Pretend to have a newly registered user
   * @returns always 'Registered'
   */
  sessionState = () => 'Registered';
}

describe('SetupTotpComponent', () => {
  let component: SetupTotpComponent;
  let fixture: ComponentFixture<SetupTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SetupTotpComponent],
      providers: [{ provide: AuthService, useClass: MockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(SetupTotpComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
