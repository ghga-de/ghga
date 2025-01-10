/**
 * Test the site header component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';

import { screen } from '@testing-library/angular';

import { SiteHeaderComponent } from './site-header.component';

/**
 * Mock the auth service as needed for the site header
 */
class MockAuthService {
  /**
   * Initiate login
   */
  login() {
    this.isLoggedIn.update(() => true);
  }

  /**
   * Initiate logout
   */
  logout(): void {
    this.isLoggedIn.set(false);
  }

  isLoggedIn = signal(false);
}

describe('SiteHeaderComponent', () => {
  let component: SiteHeaderComponent;
  let fixture: ComponentFixture<SiteHeaderComponent>;

  const fakeActivatedRoute = {
    snapshot: { data: {} },
  } as ActivatedRoute;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [NoopAnimationsModule],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    }).compileComponents();
  });

  beforeEach(async () => {
    fixture = TestBed.createComponent(SiteHeaderComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should contain a navigation', () => {
    const navbar = screen.getByRole('navigation');
    expect(navbar).toBeVisible();
  });

  it('should login and logout', async () => {
    const authService = TestBed.inject(AuthService);
    expect(authService.isLoggedIn()).toBe(false);

    const loginButton = screen.getByRole('button', { name: 'Login' });
    expect(loginButton).toBeVisible();
    expect(loginButton).toHaveTextContent('login');

    loginButton.click();

    expect(authService.isLoggedIn()).toBe(true);

    await fixture.whenStable();

    const logoutButton = screen.getByRole('button', { name: 'Logout' });
    expect(logoutButton).not.toBe(loginButton);
    expect(logoutButton).toHaveTextContent('logout');

    logoutButton.click();

    expect(authService.isLoggedIn()).toBe(false);
  });
});
