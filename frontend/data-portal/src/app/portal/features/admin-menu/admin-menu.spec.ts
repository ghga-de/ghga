/**
 * Test the administration menu component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { AdminMenuComponent } from './admin-menu';

describe('AdminMenuComponent', () => {
  let result: RenderResult<AdminMenuComponent>;

  beforeEach(async () => {
    result = await render(AdminMenuComponent, { routes: [] });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the administration menu button', () => {
    const button = screen.getByRole('button', { name: 'Administration menu' });
    expect(button).toHaveTextContent('Admin');
  });

  it('should open the menu with all items on click', async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Administration menu' }));
    const items = await screen.findAllByRole('menuitem');
    expect(items.map((item) => item.textContent?.trim())).toEqual([
      'User Manager',
      'IVA Manager',
      'Access Request Manager',
      'Access Grant Manager',
      'Upload Box Manager',
    ]);
  });
});
