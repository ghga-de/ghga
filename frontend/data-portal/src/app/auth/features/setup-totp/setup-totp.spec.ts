/**
 * Test the TOTP token setup component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { render, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

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
  needsTotpSetup = vitest.fn();
  completeTotpSetup = vitest.fn();
}

describe('SetupTotpComponent', () => {
  let component: SetupTotpComponent;
  let fixture: ComponentFixture<SetupTotpComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    ({ fixture } = await render(SetupTotpComponent, {
      providers: [{ provide: AuthService, useClass: MockAuthService }],
      routes: [],
    }));
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should welcome a newly registered user and continue the setup', async () => {
    expect(
      screen.getByText('Thank you for registering in the GHGA data portal.'),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(authService.needsTotpSetup).toHaveBeenCalledTimes(1);
  });

  it('should resolve the provisioning URI together with the secret extracted from it', async () => {
    authService.setSessionState('NeedsTotpToken');
    await expect(component.setupData()).resolves.toEqual({
      uri: TEST_URI,
      secret: 'foobar',
    });
  });

  it('should show the QR code and the setup key on request', async () => {
    authService.setSessionState('NeedsTotpToken');
    await fixture.whenStable();

    expect(await screen.findByText(/please scan this QR code/)).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: 'TOTP setup key' })).toBeNull();

    await userEvent.click(
      screen.getByRole('button', { name: 'Show manual setup instructions' }),
    );
    await fixture.whenStable();

    expect(screen.getByRole('textbox', { name: 'TOTP setup key' })).toHaveValue(
      'foobar',
    );
    expect(
      screen.getByRole('button', { name: 'Hide manual setup instructions' }),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Continue' }));

    expect(authService.completeTotpSetup).toHaveBeenCalledTimes(1);
    expect(component.allowNavigation).toBe(true);
  });

  it('should resolve to null for a session state that does not need a token', async () => {
    authService.setSessionState('Authenticated');
    await expect(component.setupData()).resolves.toBeNull();
  });

  it('should show an error with a link home when no token is needed', async () => {
    authService.setSessionState('Authenticated');
    await fixture.whenStable();

    expect(
      await screen.findByText('Error setting up two-factor authentication.'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('link', { name: 'Go back to the home page.' }),
    ).toHaveAttribute('href', '/');
  });
});
