/**
 * Tests for the Paragraphs component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { ParagraphsComponent } from './paragraphs';

describe('ParagraphsComponent', () => {
  let result: RenderResult<ParagraphsComponent>;

  beforeEach(async () => {
    result = await render(ParagraphsComponent, { inputs: { text: 'Hello\nWorld' } });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the text in multiple p tags', () => {
    const par = screen.getAllByRole('paragraph');
    expect(par.length).toBe(2);
    expect(par[0]).toHaveTextContent('Hello');
    expect(par[1]).toHaveTextContent('World');
  });

  it('should show the label when defined', async () => {
    expect(screen.queryByText('Test:')).toBeNull();
    await result.rerender({ inputs: { label: 'Test' }, partialUpdate: true });
    const strong = screen.getByText('Test:');
    expect(strong.tagName).toBe('STRONG');
  });
});
