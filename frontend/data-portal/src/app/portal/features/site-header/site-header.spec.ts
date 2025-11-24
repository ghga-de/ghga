/**
 * Test the site header component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';

import { screen } from '@testing-library/angular';

import { fakeActivatedRoute } from '@app/../mocks/route';
import { AuthService } from '@app/auth/services/auth';
import { SiteHeaderComponent } from './site-header';

/**
 * Mock the auth service as needed for the site header
 */
class MockAuthService {
  isAuthenticated = () => true;
  name = () => 'John Doe';
  fullName = () => 'Dr. John Doe';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

describe('SiteHeaderComponent', () => {
  let component: SiteHeaderComponent;
  let fixture: ComponentFixture<SiteHeaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteHeaderComponent],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SiteHeaderComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should contain a navigation', () => {
    const navbar = screen.getByRole('navigation');
    expect(navbar).toBeVisible();
  });
});
