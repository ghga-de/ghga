/**
 * Test the main app component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DeferBlockBehavior, DeferBlockState } from '@angular/core/testing';
import { render, RenderResult, screen } from '@testing-library/angular';
import { AppComponent } from './app';

import { Component } from '@angular/core';
import { SiteFooterComponent } from './portal/features/site-footer/site-footer';
import { SiteHeaderComponent } from './portal/features/site-header/site-header';
import { ConfigService } from './shared/services/config';

/**
 * Mock the config service as needed for the main app component
 */
class MockConfigService {
  ribbonText = 'Test ribbon';
}

/**
 * Mock the site header component
 */
@Component({
  selector: 'app-site-header',
  template: '<header>Mock Header</header>',
})
class MockSiteHeaderComponent {}

/**
 * Mock the site footer component
 */
@Component({
  selector: 'app-site-footer',
  template: '<footer>Mock Footer</footer>',
})
class MockSiteFooterComponent {}

describe('AppComponent', () => {
  let result: RenderResult<AppComponent>;

  beforeEach(async () => {
    result = await render(AppComponent, {
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
      importOverrides: [
        { replace: SiteHeaderComponent, with: MockSiteHeaderComponent },
        { replace: SiteFooterComponent, with: MockSiteFooterComponent },
      ],
      deferBlockBehavior: DeferBlockBehavior.Manual,
      // Keep the injector alive for the Umami initialisation the app schedules when idle
      configureTestBed: (testBed) =>
        testBed.configureTestingModule({ teardown: { destroyAfterEach: false } }),
      routes: [],
    });
  });

  it('should create the app component', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should have a header element', () => {
    expect(screen.getAllByRole('banner')[0]).toHaveTextContent('Mock Header');
  });

  it('should have a main element', () => {
    expect(screen.getByRole('main')).toBeInTheDocument();
  });

  it('should have a footer element', async () => {
    expect(screen.getByRole('contentinfo')).toBeInTheDocument();
    // The footer is the second @defer block in the template.
    await result.renderDeferBlock(DeferBlockState.Complete, 1);
    expect(screen.getByText('Mock Footer')).toBeInTheDocument();
  });

  it('should have a version ribbon', async () => {
    // The ribbon is the first @defer block in the template; render it to its
    // final state since manual defer behavior does not play through triggers.
    expect(screen.queryByRole('complementary')).toBeNull();
    await result.renderDeferBlock(DeferBlockState.Complete, 0);
    const ribbon = screen.getByRole('complementary');
    expect(ribbon).not.toBeNull();
    expect(ribbon).toHaveTextContent('Test ribbon');
  });

  it('should have a link to skip to the content', () => {
    expect(screen.getByRole('link', { name: 'Skip to content' })).toHaveAttribute(
      'href',
      '#content',
    );
  });
});
