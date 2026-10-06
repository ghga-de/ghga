/**
 * Test the home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { PageNotFoundComponent } from './page-not-found';

describe('PageNotFoundComponent', () => {
  let result: RenderResult<PageNotFoundComponent>;

  beforeEach(async () => {
    result = await render(PageNotFoundComponent);
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should render the correct content in the <h1> tag', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent(/^Page not found$/);
  });

  it('should contain the correct description text', () => {
    const paragraph = screen.getByRole('paragraph');
    expect(paragraph).toHaveTextContent(
      "Sorry, we can't seem to find the page you're looking for",
    );
  });
});
