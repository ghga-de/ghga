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

describe('VersionRibbon with build metadata', () => {
  it('should show the build metadata on a second line', async () => {
    const result = await render(VersionRibbon, {
      providers: [
        {
          provide: ConfigService,
          useValue: { ribbonText: 'Dev v15.3.1-rc.8+dev.62.93cb037' },
        },
      ],
    });
    const lines = [...result.container.querySelectorAll('aside span')];
    expect(lines.map((line) => line.textContent)).toEqual([
      'Dev v15.3.1-rc.8',
      '+dev.62.93cb037',
    ]);
  });
});
