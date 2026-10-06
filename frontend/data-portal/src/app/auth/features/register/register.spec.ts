/**
 * Test the user registration component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserSession } from '@app/auth/models/user';
import { AuthService } from '@app/auth/services/auth';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { RegisterComponent } from './register';

const USER: UserSession = {
  name: 'John Doe',
  title: 'Dr.',
  full_name: 'Dr. John Doe',
  email: 'john@ghga.de',
  state: 'LoggedIn',
  roles: [],
  csrf: 'dummy-csrf',
  ext_id: 'john@op.dev',
};

/**
 * Mock the auth service as needed for the registration component
 */
class MockAuthService {
  /** A dummy user with data from first factor authentication */
  user = signal<UserSession>(USER);
}

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;
  let authService: MockAuthService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [{ provide: AuthService, useClass: MockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
    authService = TestBed.inject(AuthService) as unknown as MockAuthService;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  /**
   * Get the select for the academic title
   * @returns the combobox
   */
  function titleSelect() {
    return screen.getByRole('combobox', { name: 'Academic title:' });
  }

  it('should pre-populate the title of the user', () => {
    expect(titleSelect()).toHaveTextContent('Dr.');
  });

  it('should follow a change of the title in the session', async () => {
    authService.user.set({ ...USER, title: 'Prof.' });
    await fixture.whenStable();
    expect(titleSelect()).toHaveTextContent('Prof.');
  });

  it('should keep the chosen title when the session has none', async () => {
    await userEvent.click(titleSelect());
    await userEvent.click(screen.getByRole('option', { name: 'Prof.' }));
    authService.user.set({ ...USER, title: null });
    await fixture.whenStable();
    expect(titleSelect()).toHaveTextContent('Prof.');
  });
});
