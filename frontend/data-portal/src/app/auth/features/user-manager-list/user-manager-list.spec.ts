/**
 * User Manager List component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { UserService } from '@app/auth/services/user';
import { ConfigService } from '@app/shared/services/config';
import { UserManagerListComponent } from './user-manager-list';

/**
 * Mock ConfigService for testing
 */
class MockConfigService {
  auth_url = 'https://test-auth.example.com';
}

/**
 * Mock UserService for testing
 */
class MockUserService {
  users = {
    value: vitest.fn(() => []),
    isLoading: vitest.fn(() => false),
    error: vitest.fn(() => null),
  };
  usersFiltered = () => this.users.value();
  ambiguousUserIds = vitest.fn(() => new Set<string>());
}

/**
 * Mock Router for testing
 */
class MockRouter {
  navigate = vitest.fn();
}

describe('UserManagerListComponent', () => {
  let component: UserManagerListComponent;
  let fixture: ComponentFixture<UserManagerListComponent>;
  let mockUserService: MockUserService;
  let mockRouter: MockRouter;

  beforeEach(async () => {
    mockUserService = new MockUserService();
    mockRouter = new MockRouter();

    await TestBed.configureTestingModule({
      imports: [UserManagerListComponent],
      providers: [
        { provide: UserService, useValue: mockUserService },
        { provide: ConfigService, useClass: MockConfigService },
        { provide: Router, useValue: mockRouter },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UserManagerListComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display loading message when users are loading', () => {
    mockUserService.users.isLoading.mockReturnValue(true);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Loading users...');
  });

  it('should display "No users found" when no users exist', () => {
    mockUserService.users.isLoading.mockReturnValue(false);
    mockUserService.users.value.mockReturnValue([]);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('No users found');

    // Check that the colspan is correct for 7 columns
    const noDataCell = compiled.querySelector('[colspan="7"]');
    expect(noDataCell).toBeTruthy();
  });

  it('should initialize table data source', () => {
    expect(component.source).toBeDefined();
    expect(component.source.data).toEqual([]);
  });

  it('should have correct default pagination settings', () => {
    expect(component.defaultTablePageSize).toBe(10);
    expect(component.tablePageSizeOptions).toEqual([10, 25, 50, 100, 250, 500]);
  });

  it('should format display name with title when available', () => {
    const usersWithVariousTitles = [
      {
        name: 'John Doe',
        title: 'Dr.' as const,
        roles: ['data_steward'],
        displayName: 'Dr. John Doe',
        roleNames: ['Data Steward'],
        sortName: 'Doe, John, Dr.',
      },
      {
        name: 'Jane Smith',
        roles: ['data_steward'],
        displayName: 'Jane Smith',
        roleNames: ['Data Steward'],
        sortName: 'Smith, Jane',
      },
      {
        name: 'Jeffrey Spencer Slate Sr.',
        title: 'Prof.' as const,
        roles: ['data_steward'],
        displayName: 'Prof. Jeffrey Spencer Slate Sr.',
        roleNames: ['Data Steward'],
        sortName: 'Slate, Jeffrey Spencer Sr., Prof.',
      },
      {
        name: 'Thomas H. Morgan Sr.',
        title: 'Prof.' as const,
        roles: [],
        displayName: 'Prof. Thomas H. Morgan Sr.',
        roleNames: [],
        sortName: 'Morgan, Thomas H. Sr., Prof.',
      },
    ] as any;

    mockUserService.users.value.mockReturnValue(usersWithVariousTitles);

    const users = component.users();

    expect(users[0].displayName).toBe('Dr. John Doe');
    expect(users[0].sortName).toBe('Doe, John, Dr.');
    expect(users[0].roleNames).toEqual(['Data Steward']);

    expect(users[1].displayName).toBe('Jane Smith');
    expect(users[1].sortName).toBe('Smith, Jane');
    expect(users[1].roleNames).toEqual(['Data Steward']);

    expect(users[2].displayName).toBe('Prof. Jeffrey Spencer Slate Sr.');
    expect(users[2].sortName).toBe('Slate, Jeffrey Spencer Sr., Prof.');
    expect(users[2].roleNames).toEqual(['Data Steward']);

    expect(users[3].displayName).toBe('Prof. Thomas H. Morgan Sr.');
    expect(users[3].sortName).toBe('Morgan, Thomas H. Sr., Prof.');
    expect(users[3].roleNames).toEqual([]);
  });

  it('should navigate to user details when viewDetails is called', () => {
    const mockUser = { id: '123', name: 'Test User' } as any;
    component.viewDetails(mockUser);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/user-manager', '123']);
  });
});
