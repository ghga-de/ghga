/**
 * Tests for the "with copy button" component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { Notifier } from '@app/shared/services/notification';
import { WithCopyButton } from './with-copy-button';

describe('WithCopyButton', () => {
  let result: RenderResult<WithCopyButton>;
  const mockNotificationService = { showInfo: vitest.fn() };

  beforeEach(async () => {
    mockNotificationService.showInfo.mockClear();
    result = await render(WithCopyButton, {
      inputs: { value: 'some-long-identifier' },
      providers: [{ provide: Notifier, useValue: mockNotificationService }],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the value with a copy button', async () => {
    expect(screen.getByTitle('some-long-identifier')).toHaveTextContent(
      'some-long-identifier',
    );
    await userEvent.click(
      screen.getByRole('button', { name: 'Copy full text to clipboard' }),
    );
    expect(mockNotificationService.showInfo).toHaveBeenCalledWith(
      'The full text has been copied to clipboard',
      1000,
    );
  });

  it('should show N/A without a value', async () => {
    await result.rerender({ inputs: { value: '' }, partialUpdate: true });
    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });
});
