/**
 * Testing for the site header nav buttons component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { AuthService } from '@app/auth/services/auth';
import { SiteHeaderNavButtonsComponent } from './site-header-nav-buttons';

/**
 * Mock the auth service as needed for the site header nav buttons
 */
class MockAuthService {
  roles = () => ['data_steward'];
}

describe('SiteHeaderNavButtonsComponent', () => {
  let result: RenderResult<SiteHeaderNavButtonsComponent>;

  beforeEach(async () => {
    result = await render(SiteHeaderNavButtonsComponent, {
      providers: [{ provide: AuthService, useClass: MockAuthService }],
      routes: [],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the navigation links', () => {
    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/');
    expect(screen.getByRole('link', { name: 'Browse Data' })).toHaveAttribute(
      'href',
      '/browse',
    );
  });

  it('should show the admin menu for data stewards', () => {
    expect(
      screen.getByRole('button', { name: 'Administration menu' }),
    ).toBeInTheDocument();
  });
});
