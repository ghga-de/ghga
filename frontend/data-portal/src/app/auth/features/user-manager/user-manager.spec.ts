/**
 * User Manager component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNativeDateAdapter } from '@angular/material/core';
import { UserService } from '@app/auth/services/user';
import { ConfigService } from '@app/shared/services/config';
import { UserManagerComponent } from './user-manager';

/**
 * Mock ConfigService for testing
 */
class MockConfigService {
  auth_url = 'https://test-auth.example.com';
}

/**
 * Mock the user service as needed by the user manager child components
 */
class MockUserService {
  loadUsers = () => undefined;
  setUsersFilter = () => undefined;
  users = {
    value: () => [],
    isLoading: () => false,
    error: () => undefined,
  };
  usersFilter = () => ({
    idStrings: '',
    role: undefined,
    status: undefined,
  });
  usersFiltered = () => this.users.value();
  ambiguousUserIds = () => new Set();
}

describe('UserManagerComponent', () => {
  let component: UserManagerComponent;
  let fixture: ComponentFixture<UserManagerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserManagerComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNativeDateAdapter(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: UserService, useClass: MockUserService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserManagerComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have userService injected', () => {
    expect(component.userService).toBeDefined();
  });

  it('should render the title', () => {
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('User Management');
  });

  it('should render filter and list', () => {
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('app-user-manager-filter')).toBeTruthy();
    expect(compiled.querySelector('app-user-manager-list')).toBeTruthy();
  });
});
