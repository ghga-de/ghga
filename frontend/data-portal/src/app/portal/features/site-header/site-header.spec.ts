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
import { SiteHeader } from './site-header';

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

describe('SiteHeader', () => {
  let component: SiteHeader;
  let fixture: ComponentFixture<SiteHeader>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SiteHeader],
      providers: [
        { provide: AuthService, useClass: MockAuthService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SiteHeader);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should contain a navigation', () => {
    const navbar = screen.getByRole('navigation', { hidden: true });
    expect(navbar).toBeInTheDocument();
  });
});
