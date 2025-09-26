/**
 * User Manager component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNativeDateAdapter } from '@angular/material/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
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
 * Mock UserService for testing
 */
const MockUserService = {
  loadUsers: jest.fn(),
};

describe('UserManagerComponent', () => {
  let component: UserManagerComponent;
  let fixture: ComponentFixture<UserManagerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [UserManagerComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNativeDateAdapter(),
        { provide: ConfigService, useClass: MockConfigService },
        { provide: UserService, useValue: MockUserService },
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
