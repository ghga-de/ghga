/**
 * Test the version ribbon component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

import { ConfigService } from '@app/shared/services/config';
import { VersionRibbon } from './version-ribbon';

/**
 * Mock the config service as needed by the version ribbon component
 */
class MockConfigService {
  ribbonText = 'Test ribbon text';
}

describe('VersionRibbon', () => {
  let result: RenderResult<VersionRibbon>;

  beforeEach(async () => {
    result = await render(VersionRibbon, {
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the ribbon text', () => {
    const text = result.container.textContent;
    expect(text).toBe('Test ribbon text');
  });

  it('should remove the ribbon text on click', async () => {
    const aside = screen.getByRole('complementary');
    expect(aside).toBeTruthy();
    expect(aside).toHaveTextContent(/^Test ribbon text$/);
    await userEvent.click(aside);
    await result.fixture.whenStable();
    expect(screen.queryByRole('complementary')).toBeNull();
    expect(result.container.textContent).toBe('');
  });
});
