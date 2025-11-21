/**
 * Testing for the site header nav buttons component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AuthService } from '@app/auth/services/auth';
import { AccountButtonComponent } from '../../../auth/features/account-button/account-button';
import { AdminMenuComponent } from '../admin-menu/admin-menu';
import { SiteHeaderNavButtonsComponent } from './site-header-nav-buttons';

/**
 * Mock the auth service as needed for the admin menu
 */
class MockAuthService {
  roles = () => ['data_steward'];
}

describe('SiteHeaderNavButtonsComponent', () => {
  let component: SiteHeaderNavButtonsComponent;
  let fixture: ComponentFixture<SiteHeaderNavButtonsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteHeaderNavButtonsComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        {
          provide: ActivatedRoute,
          useValue: fakeActivatedRoute,
        },
      ],
    })
      .overrideComponent(SiteHeaderNavButtonsComponent, {
        remove: {
          imports: [AccountButtonComponent, AdminMenuComponent],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(SiteHeaderNavButtonsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
