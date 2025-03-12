/**
 * Test the account button component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { computed, signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { screen } from '@testing-library/angular';

import { RoleNames, User } from '@app/auth/models/user';
import { AuthService } from '@app/auth/services/auth.service';

import { AccountButtonComponent } from './account-button.component';

/**
 * A dummy user object with only the properties needed by the account button
 */
export const USER = {
  name: 'John Doe',
  title: 'Dr.',
  full_name: 'Dr. John Doe',
  roles: ['data_steward'],
  state: 'Authenticated',
} as User;

/**
 * Mock the auth service as needed for the account button
 */
class MockAuthService {
  /**
   * Initiate login
   */
  login() {
    this.isLoggedIn.update(() => true);
    this.isAuthenticated.update(() => true);
  }

  /**
   * Initiate logout
   */
  logout(): void {
    this.isLoggedIn.set(false);
  }

  isLoggedIn = signal(false);
  isAuthenticated = signal(false);

  sessionState = computed(() =>
    this.isAuthenticated() ? 'Authenticated' : 'LoggedOut',
  );
  user = computed(() => (this.isAuthenticated() ? USER : null));
  name = computed(() => this.user()?.name);
  fullName = computed(() => this.user()?.full_name);
  roles = computed(() => this.user()?.roles ?? []);
  roleNames = computed(() =>
    this.roles() ? this.roles().map((role) => RoleNames[role]) : [],
  );
}

describe('AccountButtonComponent', () => {
  let component: AccountButtonComponent;
  let fixture: ComponentFixture<AccountButtonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AccountButtonComponent],
      providers: [{ provide: AuthService, useClass: MockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(AccountButtonComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should login and logout', async () => {
    const authService = TestBed.inject(AuthService);
    expect(authService.isLoggedIn()).toBe(false);

    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    const loginButton = screen.getByRole('button', { name: 'Log in' });
    expect(loginButton).toBeVisible();
    loginButton.click();

    const loginMenu = screen.getByRole('menu');
    expect(loginMenu).toBeVisible();

    expect(authService.isLoggedIn()).toBe(false);

    const lsLoginButton = screen.getByRole('menuitem', { name: 'LS Login' });
    expect(lsLoginButton).toBeVisible();
    lsLoginButton.click();

    expect(authService.isLoggedIn()).toBe(true);

    await fixture.whenStable();

    const accountButton = screen.getByRole('button', { name: 'Account' });
    expect(accountButton).toBeVisible();
    accountButton.click();

    const accountMenu = screen.getByRole('menu');
    expect(accountMenu).toBeVisible();
    expect(accountMenu).not.toBe(loginMenu);

    expect(authService.isLoggedIn()).toBe(true);

    const logoutButton = screen.getByRole('menuitem', { name: 'Log out' });
    expect(logoutButton).toBeVisible();
    logoutButton.click();

    expect(authService.isLoggedIn()).toBe(false);
  });
});
