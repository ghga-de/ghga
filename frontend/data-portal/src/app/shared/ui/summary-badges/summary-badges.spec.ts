/**
 * Test the summary badges component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { SummaryBadgesComponent } from './summary-badges';

describe('SummaryBadgesComponent', () => {
  let result: RenderResult<SummaryBadgesComponent>;

  beforeEach(async () => {
    result = await render(SummaryBadgesComponent, {
      inputs: {
        data: [
          { value: 'test 1', count: 1 },
          { value: 'test 2', count: 1 },
          { value: 'test 3', count: 1 },
          { value: 'test 4', count: 1 },
        ],
      },
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show "Show 2 More" when there are four items', () => {
    const text = result.container.textContent;
    expect(text).toContain('test 1 1test 2 1Show 2 more…test 3 1test 4 1');
    expect(screen.getByText('Show 2 more…')).toBeInTheDocument();
  });

  it('should toggle between showing more and less on click', async () => {
    await userEvent.click(screen.getByText('Show 2 more…'));
    await result.fixture.whenStable();
    expect(screen.queryByText('Show 2 more…')).toBeNull();
    await userEvent.click(screen.getByText('Show less…'));
    await result.fixture.whenStable();
    expect(screen.getByText('Show 2 more…')).toBeInTheDocument();
  });

  it('should show all three data points when there are only three', async () => {
    await result.rerender({
      inputs: {
        data: [
          { value: 'test 1', count: 1 },
          { value: 'test 2', count: 1 },
          { value: 'test 3', count: 1 },
        ],
      },
      partialUpdate: true,
    });
    const text = result.container.textContent;
    expect(text).toContain('test 1 1test 2 1test 3 1');
    expect(screen.queryByText(/more…/)).toBeNull();
  });
});
