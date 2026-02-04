/**
 * User Manager Detail component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { allIvasOfDoe } from '@app/../mocks/data';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { UserService } from '@app/auth/services/user';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { UserManagerComponent } from '../user-manager/user-manager';
import { UserManagerDetailComponent } from './user-manager-detail';

/**
 * Mock the IVA service as needed by the user manager dialog component
 */
class MockIvaService {
  loadUserIvas = () => undefined;
  userIvas = {
    value: () => allIvasOfDoe,
    isLoading: () => false,
    error: () => undefined,
  };
}

/**
 * Mock UserService for testing
 */
class MockUserService {
  users = {
    value: vitest.fn(() => [
      {
        id: '123',
        name: 'John Doe',
        displayName: 'Dr. John Doe',
        title: 'Dr.',
        email: 'john@example.com',
        ext_id: 'ext123',
        roles: ['data_steward'],
        roleNames: ['Data Steward'],
        status: 'active',
        registration_date: '2023-01-01',
        sortName: 'Doe, John, Dr.',
      },
      {
        id: '456',
        name: 'Jane Smith',
        displayName: 'Jane Smith',
        email: 'jane.smith@example.com',
        ext_id: 'ext456',
        roles: ['data_contributor'],
        roleNames: ['Data Contributor'],
        status: 'active',
        registration_date: '2023-01-02',
        sortName: 'Smith, Jane',
      },
    ]),
    isLoading: vitest.fn(() => false),
    error: vitest.fn(() => null),
  };
  loadUsers = () => undefined;

  user = {
    value: vitest.fn(() => {
      return {
        id: '123',
        name: 'John Doe',
        displayName: 'Dr. John Doe',
        title: 'Dr.',
        email: 'john@example.com',
        ext_id: 'ext123',
        roles: ['data_steward'],
        roleNames: ['Data Steward'],
        status: 'active',
        registration_date: '2023-01-01',
        sortName: 'Doe, John, Dr.',
      };
    }),
    isLoading: vitest.fn(() => false),
    error: vitest.fn(() => null),
  };
  loadUser = () => undefined;
  deleteUser = () => undefined;
  updateUser = () => undefined;

  createUserResource = () => ({
    load: () => undefined,
    resource: {
      value: () => undefined,
      isLoading: () => false,
      error: () => undefined,
    },
  });
}

describe('UserManagerDetailComponent', () => {
  let component: UserManagerDetailComponent;
  let fixture: ComponentFixture<UserManagerDetailComponent>;
  let navigation: NavigationTrackingService;
  let mockUserService = new MockUserService();

  beforeEach(async () => {
    const testBed = TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent],
      providers: [
        provideRouter([
          { path: 'user-manager/doe@test.dev', component: UserManagerDetailComponent },
          { path: 'user-manager', component: UserManagerComponent },
        ]),
        CommonDatePipe,
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    }).overrideComponent(UserManagerDetailComponent, {
      set: {
        // the user service is provided at the component level
        providers: [{ provide: UserService, useValue: mockUserService }],
      },
    });
    await testBed.compileComponents();
    navigation = testBed.inject(NavigationTrackingService);

    fixture = TestBed.createComponent(UserManagerDetailComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('id', 'doe@test.dev');

    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should find and display user when ID matches', () => {
    fixture.detectChanges();

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
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('User: Dr. John Doe');
    expect(compiled.textContent).toContain('john@example.com');
    expect(compiled.textContent).toContain('ext123');
    expect(compiled.textContent).toContain('Data Steward');
  });

  it('should show not found message when user is not found', () => {
    // Create a new mock that returns empty array
    const emptyMockUserService = {
      user: {
        value: vitest.fn(() => undefined),
        isLoading: vitest.fn(() => false),
        error: vitest.fn(() => new HttpErrorResponse({ status: 404 })),
      },
      users: {
        value: vitest.fn(() => []),
        isLoading: vitest.fn(() => false),
        error: vitest.fn(() => null),
      },
      loadUser: () => undefined,
      createUserResource: () => undefined,
      filter: () => {
        idStrings: [];
      },
    };

    // Create a new component with the updated mock
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: UserService, useValue: emptyMockUserService },
      ],
    }).compileComponents();

    const emptyFixture = TestBed.createComponent(UserManagerDetailComponent);
    emptyFixture.componentRef.setInput('id', 'error');
    emptyFixture.detectChanges();
    const compiled = emptyFixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('The selected user could not be found');
  });

  it('should reload when id input changes', async () => {
    const loadUserSpy = vitest.spyOn(mockUserService, 'loadUser');

    fixture.detectChanges();
    expect(component.user()?.id).toBe('123');

    mockUserService.user.value = vitest.fn(() => ({
      id: '456',
      name: 'Jane Smith',
      displayName: 'Jane Smith',
      title: '',
      email: 'jane.smith@example.com',
      ext_id: 'ext456',
      roles: ['data_contributor'],
      roleNames: ['Data Contributor'],
      status: 'active',
      registration_date: '2023-01-02',
      sortName: 'Smith, Jane',
    }));

    fixture.componentRef.setInput('id', '456');
    fixture.detectChanges();
    await fixture.whenStable();

    // user 456 exists in users list mock -> loadUser should NOT be called
    expect(loadUserSpy).not.toHaveBeenCalled();
    expect(component.user()?.id).toBe('456');
    expect(component.user()?.name).toBe('Jane Smith');
  });
});
