/**
 * User Manager Detail component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MatDialog } from '@angular/material/dialog';
import { allIvasOfDoe } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { UserStatus } from '@app/auth/models/user';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTracker } from '@app/shared/services/navigation';
import { render, RenderResult, screen } from '@testing-library/angular';
import { UserManager } from '../user-manager/user-manager';
import { UserManagerDetail } from './user-manager-detail';

const JOHN_DOE: DisplayUser = {
  id: '123',
  name: 'John Doe',
  displayName: 'Dr. John Doe',
  title: 'Dr.',
  email: 'john@example.com',
  ext_id: 'ext123',
  roles: ['data_steward'],
  roleNames: ['Data Steward'],
  status: UserStatus.active,
  registration_date: '2023-01-01',
  sortName: 'Doe, John, Dr.',
};

// cast because the portal's user roles do not include data contributors
const JANE_SMITH = {
  id: '456',
  name: 'Jane Smith',
  displayName: 'Jane Smith',
  email: 'jane.smith@example.com',
  ext_id: 'ext456',
  roles: ['data_contributor'],
  roleNames: ['Data Contributor'],
  status: UserStatus.active,
  registration_date: '2023-01-02',
  sortName: 'Smith, Jane',
} as unknown as DisplayUser;

/**
 * Mock the IVA service as needed by the user manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  ivaError = signal<Error | undefined>(undefined);
  userIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: this.ivaError,
  };
}

/**
 * Mock UserService for testing, with signals that the tests can change
 */
class MockUserService {
  usersValue = signal<DisplayUser[]>([JOHN_DOE, JANE_SMITH]);
  users = {
    value: this.usersValue.asReadonly(),
    isLoading: signal(false).asReadonly(),
    error: signal(null).asReadonly(),
  };
  loadUsers = () => undefined;

  userValue = signal<DisplayUser | undefined>(JOHN_DOE);
  userError = signal<HttpErrorResponse | null>(null);
  user = {
    value: this.userValue.asReadonly(),
    isLoading: signal(false).asReadonly(),
    error: this.userError.asReadonly(),
  };
  loadUser = vitest.fn();
  deleteUser = () => undefined;
  updateUser = () => undefined;

  createUserFetcher = () => ({
    load: () => undefined,
    resource: {
      value: () => undefined,
      isLoading: () => false,
      error: () => undefined,
    },
  });
}

describe('UserManagerDetail', () => {
  let result: RenderResult<UserManagerDetail>;
  let component: UserManagerDetail;
  let fixture: ComponentFixture<UserManagerDetail>;
  let navigation: NavigationTracker;
  let mockUserService: MockUserService;

  beforeEach(async () => {
    mockUserService = new MockUserService();
    result = await render(UserManagerDetail, {
      inputs: { id: 'doe@test.dev' },
      providers: [
        CommonDatePipe,
        { provide: UserService, useValue: mockUserService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
      routes: [
        { path: 'user-manager/doe@test.dev', component: UserManagerDetail },
        { path: 'user-manager', component: UserManager },
      ],
    });
    navigation = TestBed.inject(NavigationTracker);
    fixture = result.fixture;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should find and display user when ID matches', () => {
    const user = component.user();
    expect(user).toBeDefined();
    expect(user?.name).toBe('John Doe');
    expect(user?.title).toBe('Dr.');
  });

  it('should navigate back when goBack is called', async () => {
    vitest.spyOn(navigation, 'back');
    component.goBack();
    await new Promise((resolve) => setTimeout(resolve));
    expect(navigation.back).toHaveBeenCalled();
  });

  it('should render user details when user is found', () => {
    expect(
      screen.getByRole('heading', { level: 1, name: 'User: Dr. John Doe' }),
    ).toBeInTheDocument();
    expect(screen.getByText('Dr.')).toBeInTheDocument();
    expect(screen.getByText('John Doe')).toBeInTheDocument();
    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('ext123')).toBeInTheDocument();
    expect(screen.getByText('Data Steward')).toBeInTheDocument();
  });

  it('should show an error message when the IVAs could not be loaded', async () => {
    const ivaService = TestBed.inject(IvaService) as unknown as MockIvaService;
    ivaService.ivaError.set(new Error('Internal server error'));
    await fixture.whenStable();

    expect(screen.getByText(/The IVAs could\s+not be loaded/)).toBeInTheDocument();
  });

  it('should show not found message when user is not found', async () => {
    mockUserService.usersValue.set([]);
    mockUserService.userValue.set(undefined);
    mockUserService.userError.set(new HttpErrorResponse({ status: 404 }));
    await result.rerender({ inputs: { id: 'error' }, partialUpdate: true });
    await fixture.whenStable();

    expect(
      screen.getByText('The selected user could not be found.'),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 1, name: 'User Details' }),
    ).toBeInTheDocument();
  });

  it('should let the deletion dialog use its UserService', () => {
    const dialog = fixture.debugElement.injector.get(MatDialog);
    const open = vitest.spyOn(dialog, 'open').mockReturnValue(undefined as never);
    component.safeDeletion();
    expect(open.mock.calls[0][1]?.injector?.get(UserService)).toBe(mockUserService);
  });

  it('should reload when id input changes', async () => {
    mockUserService.loadUser.mockClear();
    expect(component.user()?.id).toBe('123');

    mockUserService.userValue.set(JANE_SMITH);
    await result.rerender({ inputs: { id: '456' }, partialUpdate: true });
    await fixture.whenStable();

    // user 456 exists in users list mock -> loadUser should NOT be called
    expect(mockUserService.loadUser).not.toHaveBeenCalled();
    expect(component.user()?.id).toBe('456');
    expect(component.user()?.name).toBe('Jane Smith');
    expect(
      screen.getByRole('heading', { level: 1, name: 'User: Jane Smith' }),
    ).toBeInTheDocument();
  });
});
