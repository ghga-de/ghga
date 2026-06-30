/**
 * Test the user registration component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserSession } from '@app/auth/models/user';
import { AuthService } from '@app/auth/services/auth';
import { RegisterComponent } from './register';

/**
 * Mock the auth service as needed for the registration component
 */
class MockAuthService {
  /**
   * Provide a dummy user with data from first factor authentication
   * @returns a dummy user with all properties set
   */
  user(): UserSession {
    return {
      name: 'John Doe',
      title: 'Dr.',
      full_name: 'Dr. John Doe',
      email: 'john@ghga.de',
      state: 'LoggedIn',
      roles: [],
      csrf: 'dummy-csrf',
      ext_id: 'john@op.dev',
    };
  }
}

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RegisterComponent],
      providers: [{ provide: AuthService, useClass: MockAuthService }],
    }).compileComponents();

    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
