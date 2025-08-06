/**
 * User Manager Detail component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe, Location } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { allIvasOfDoe } from '@app/../mocks/data';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { UserService } from '@app/auth/services/user.service';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { UserManagerDetailComponent } from './user-manager-detail.component';

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
    value: jest.fn(() => [
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
    isLoading: jest.fn(() => false),
    error: jest.fn(() => null),
  };
  loadUsers = () => undefined;

  user = {
    value: jest.fn(() => {
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
    isLoading: jest.fn(() => false),
    error: jest.fn(() => null),
  };
  loadUser = () => undefined;
  deleteUser = () => undefined;
  updateUser = () => undefined;
}

describe('UserManagerDetailComponent', () => {
  let component: UserManagerDetailComponent;
  let fixture: ComponentFixture<UserManagerDetailComponent>;
  let location: Location;
  let mockUserService = new MockUserService();

  beforeEach(async () => {
    const testBed = TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent],
      providers: [
        provideNoopAnimations(),
        provideRouter([
          { path: 'user-manager/doe@test.dev', component: UserManagerDetailComponent },
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
    location = testBed.inject(Location);

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
    jest.spyOn(location, 'back');
    component.goBack();
    await new Promise((resolve) => setTimeout(resolve));
    expect(location.back).toHaveBeenCalled();
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
        value: jest.fn(() => undefined),
        isLoading: jest.fn(() => false),
        error: jest.fn(() => new HttpErrorResponse({ status: 404 })),
      },
      users: {
        value: jest.fn(() => []),
        isLoading: jest.fn(() => false),
        error: jest.fn(() => null),
      },
      loadUser: () => undefined,
    };

    // Create a new component with the updated mock
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent],
      providers: [
        provideNoopAnimations(),
        { provide: IvaService, useClass: MockIvaService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
      ],
    })
      .overrideComponent(UserManagerDetailComponent, {
        set: {
          providers: [{ provide: UserService, useValue: emptyMockUserService }],
        },
      })
      .compileComponents();

    const emptyFixture = TestBed.createComponent(UserManagerDetailComponent);
    emptyFixture.componentRef.setInput('id', 'error');
    emptyFixture.detectChanges();
    const compiled = emptyFixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('The selected user could not be found');
  });
});
