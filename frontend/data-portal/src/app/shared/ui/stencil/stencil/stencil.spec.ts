/**
 * Test the stencil component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { Stencil } from './stencil';

describe('Stencil', () => {
  let result: RenderResult<Stencil>;

  beforeEach(async () => {
    result = await render(Stencil);
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show one busy loader with the default label', () => {
    const loader = screen.getByRole('loader', { name: 'loading' });
    expect(loader).toHaveAttribute('aria-busy', 'true');
    expect(loader).toHaveAttribute('aria-valuetext', 'Loading...');
  });

  it('should show as many loaders as requested', async () => {
    await result.rerender({
      inputs: { count: 3, label: 'waiting' },
      partialUpdate: true,
    });
    expect(screen.getAllByRole('loader', { name: 'waiting' })).toHaveLength(3);
  });
});
