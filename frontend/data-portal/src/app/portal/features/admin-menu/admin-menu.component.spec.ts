/**
 * Test the administration menu component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';
import { AdminMenuComponent } from './admin-menu.component';

/**
 * Mock the auth service as needed for the admin menu
 */
class MockAuthService {
  role = () => 'data_steward';
}

const fakeActivatedRoute = {
  snapshot: { data: {}, url: [{ path: 'iva-manager' }] },
} as ActivatedRoute;

describe('AdminMenuComponent', () => {
  let component: AdminMenuComponent;
  let fixture: ComponentFixture<AdminMenuComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AdminMenuComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AdminMenuComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
