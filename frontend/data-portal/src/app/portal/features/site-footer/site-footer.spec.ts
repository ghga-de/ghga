/**
 * Test the site footer component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { SiteFooter } from './site-footer';

describe('SiteFooter', () => {
  let result: RenderResult<SiteFooter>;

  beforeEach(async () => {
    result = await render(SiteFooter, { routes: [] });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should contain the footer navigation with its links', () => {
    const nav = screen.getByRole('navigation', { name: 'Footer navigation' });
    expect(nav).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Data Portal Home Page' })).toHaveAttribute(
      'href',
      '/',
    );
    expect(screen.getByRole('link', { name: 'Browse Data' })).toHaveAttribute(
      'href',
      '/browse',
    );
  });

  it('should show the copyright notice for the current year', () => {
    const year = new Date().getFullYear();
    expect(screen.getByText(`©${year} GHGA. All Rights Reserved.`)).toBeInTheDocument();
  });
});
