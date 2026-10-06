/**
 * Tests for the StatusTextBox
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { SchemapackOutputStatus } from '@app/tools/models/status-text';
import { StatusTextBox } from './status-text-box';

describe('StatusTextBox', () => {
  let result: RenderResult<StatusTextBox>;

  beforeEach(async () => {
    result = await render(StatusTextBox, {
      inputs: {
        status: SchemapackOutputStatus.READY,
        statusText: 'Ready. Load a default or paste your content.',
      },
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the status text', () => {
    expect(
      screen.getByText('Ready. Load a default or paste your content.'),
    ).toBeInTheDocument();
  });

  it('should show a changed status text', async () => {
    await result.rerender({
      inputs: { status: SchemapackOutputStatus.ERROR, statusText: 'Invalid input.' },
      partialUpdate: true,
    });
    expect(screen.getByText('Invalid input.')).toBeInTheDocument();
    expect(screen.queryByText(/^Ready\./)).toBeNull();
  });
});
