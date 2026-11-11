/**
 * Test the tools menu component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { ToolsMenu } from './tools-menu';

describe('ToolsMenu', () => {
  let result: RenderResult<ToolsMenu>;

  beforeEach(async () => {
    result = await render(ToolsMenu, { routes: [] });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the tools menu button', () => {
    const button = screen.getByRole('button', { name: 'Tools' });
    expect(button).toHaveTextContent('Tools');
  });

  it('should open the menu with all items on click', async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Tools' }));
    const items = await screen.findAllByRole('menuitem');
    expect(items.map((item) => item.textContent?.trim())).toEqual([
      'Metadata Validator',
      'Schemapack Playground',
    ]);
  });
});
