/**
 * Test the TOTP token setup component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AuthService } from '@app/auth/services/auth';
import { SetupTotpComponent } from './setup-totp';

const TEST_URI = 'otpauth://totp/GHGA:doe?secret=foobar&issuer=GHGA';

/**
 * Mock the auth service as needed for the setup TOTP component
 */
class MockAuthService {
  /**
   * Pretend to have determined the login state
   * @returns always false
   */
  isUndetermined = () => false;

  #sessionState = signal('Registered');

  sessionState = this.#sessionState.asReadonly();

  /**
   * Override the current session state for a test.
   * @param state - the session state to expose
   */
  setSessionState(state: string): void {
    this.#sessionState.set(state);
  }

  createTotpToken = vitest.fn(async () => TEST_URI);
}

describe('SetupTotpComponent', () => {
  let component: SetupTotpComponent;
  let fixture: ComponentFixture<SetupTotpComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SetupTotpComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useClass: MockAuthService },
      ],
    }).compileComponents();

    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    fixture = TestBed.createComponent(SetupTotpComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should resolve the provisioning URI together with the secret extracted from it', async () => {
    authService.setSessionState('NeedsTotpToken');
    await expect(component.setupData()).resolves.toEqual({
      uri: TEST_URI,
      secret: 'foobar',
    });
  });

  it('should resolve to null for a session state that does not need a token', async () => {
    authService.setSessionState('Authenticated');
    await expect(component.setupData()).resolves.toBeNull();
  });
});
