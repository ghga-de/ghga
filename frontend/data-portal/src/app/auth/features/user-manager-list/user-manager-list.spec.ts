/**
 * User Manager List component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import {
  MAT_PAGINATOR_DEFAULT_OPTIONS,
  MatPaginator,
  MatPaginatorDefaultOptions,
} from '@angular/material/paginator';
import { By } from '@angular/platform-browser';
import { Router } from '@angular/router';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { ConfigService } from '@app/shared/services/config';
import { screen } from '@testing-library/angular';
import { UserManagerListComponent } from './user-manager-list';

const WARN_TITLE = 'There are multiple user accounts with this name and email address.';
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
    value: vitest.fn((): DisplayUser[] => []),
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

const paginatorDefaults: MatPaginatorDefaultOptions = {
  pageSize: 10,
  pageSizeOptions: [10, 25, 50, 100, 250, 500],
};

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
        { provide: MAT_PAGINATOR_DEFAULT_OPTIONS, useValue: paginatorDefaults },
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

  it('should display loading message when users are loading', async () => {
    mockUserService.users.isLoading.mockReturnValue(true);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Loading users...');
  });

  it('should display "No users found" when no users exist', async () => {
    mockUserService.users.isLoading.mockReturnValue(false);
    mockUserService.users.value.mockReturnValue([]);
    await fixture.whenStable();
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

  it('should have correct default pagination settings', async () => {
    const usersWithVariousTitles: Partial<DisplayUser>[] = [];
    for (let i = 0; i < 15; i++) {
      usersWithVariousTitles.push({
        name: 'John Doe',
        title: 'Dr.' as const,
        roles: ['data_steward'],
        displayName: 'Dr. John Doe',
        roleNames: ['Data Steward'],
        sortName: 'Doe, John, Dr.',
      });
    }
    mockUserService.users.value.mockReturnValue(
      usersWithVariousTitles as unknown as DisplayUser[],
    );
    await fixture.whenStable();
    const paginatorDebugEl = fixture.debugElement.query(By.directive(MatPaginator));
    const paginator = paginatorDebugEl.componentInstance as MatPaginator;
    const defaults = TestBed.inject(MAT_PAGINATOR_DEFAULT_OPTIONS);

    expect(paginator.pageSize).toBe(defaults.pageSize);
    expect(paginator.pageSizeOptions).toEqual(defaults.pageSizeOptions);
  });

  it('should format display name with title when available', () => {
    const usersWithVariousTitles: Partial<DisplayUser>[] = [
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
    ];

    mockUserService.users.value.mockReturnValue(
      usersWithVariousTitles as unknown as DisplayUser[],
    );

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
    const mockUser = { id: '123', name: 'Test User' } as unknown as DisplayUser;
    component.viewDetails(mockUser);
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/user-manager', '123']);
  });

  it('should mark only the ambiguous users with a warning', async () => {
    const users: Partial<DisplayUser>[] = ['u1', 'u2', 'u3'].map((id) => ({
      id,
      email: `${id}@test.dev`,
      roles: [],
      displayName: `User ${id}`,
      roleNames: [],
      sortName: `User ${id}`,
    }));
    mockUserService.users.value.mockReturnValue(users as unknown as DisplayUser[]);
    mockUserService.ambiguousUserIds.mockReturnValue(new Set(['u2']));
    await fixture.whenStable();

    const markers = screen.getAllByTitle(WARN_TITLE);
    expect(markers).toHaveLength(1);
    expect(markers[0].closest('tr')).toHaveTextContent('u2@test.dev');
  });
});
