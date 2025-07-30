/**
 * User Manager Detail component tests
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { UserService } from '@app/auth/services/user.service';
import { ConfigService } from '@app/shared/services/config.service';
import { UserManagerDetailComponent } from './user-manager-detail.component';

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
}

/**
 * Mock ActivatedRoute for testing
 */
class MockActivatedRoute {
  snapshot = {
    params: { id: '123' },
  };
}

/**
 * Mock Router for testing
 */
class MockRouter {
  navigate = jest.fn();
}

describe('UserManagerDetailComponent', () => {
  let component: UserManagerDetailComponent;
  let fixture: ComponentFixture<UserManagerDetailComponent>;
  let mockUserService: MockUserService;
  let mockRouter: MockRouter;

  beforeEach(async () => {
    mockUserService = new MockUserService();
    mockRouter = new MockRouter();

    await TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        CommonDatePipe,
        { provide: ConfigService, useClass: MockConfigService },
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        { provide: Router, useValue: mockRouter },
      ],
    })
      .overrideComponent(UserManagerDetailComponent, {
        set: {
          providers: [{ provide: UserService, useValue: mockUserService }],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(UserManagerDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
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
    component.goBack();
    await new Promise((resolve) => setTimeout(resolve));
    expect(mockRouter.navigate).toHaveBeenCalledWith(['/user-manager']);
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
      users: {
        value: jest.fn(() => []),
        isLoading: jest.fn(() => false),
        error: jest.fn(() => null),
      },
    };

    // Create a new component with the updated mock
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [UserManagerDetailComponent, NoopAnimationsModule],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        CommonDatePipe,
        { provide: ConfigService, useClass: MockConfigService },
        { provide: ActivatedRoute, useClass: MockActivatedRoute },
        { provide: Router, useValue: mockRouter },
      ],
    })
      .overrideComponent(UserManagerDetailComponent, {
        set: {
          providers: [{ provide: UserService, useValue: emptyMockUserService }],
        },
      })
      .compileComponents();

    const emptyFixture = TestBed.createComponent(UserManagerDetailComponent);
    emptyFixture.detectChanges();
    const compiled = emptyFixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('User Not Found');
  });
});
