/**
 * Testing for the site header nav buttons component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { AuthService } from '@app/auth/services/auth';
import { SiteHeaderNavButtonsComponent } from './site-header-nav-buttons';

/**
 * Mock the auth service as needed for the site header nav buttons
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
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SiteHeaderNavButtonsComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
