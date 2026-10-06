/**
 * Test the home page component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DeferBlockState } from '@angular/core/testing';
import { render, RenderResult, screen } from '@testing-library/angular';

import { HomePageComponent } from './home-page';

import { metadataGlobalSummary } from '@app/../mocks/data';
import { GlobalSummaryComponent } from '@app/metadata/features/global-summary/global-summary';
import { MetadataStatsService } from '@app/metadata/services/metadata-stats';

/**
 * Mock the metadata service as needed for the home page
 */
class MockMetadataStatsService {
  globalSummary = {
    value: () => metadataGlobalSummary.resource_stats,
    isLoading: () => false,
    error: () => undefined,
  };
}

describe('HomePageComponent', () => {
  let result: RenderResult<HomePageComponent>;

  beforeEach(async () => {
    result = await render(HomePageComponent, {
      routes: [],
      deferBlockStates: DeferBlockState.Complete,
      childComponentOverrides: [
        {
          component: GlobalSummaryComponent,
          providers: [
            { provide: MetadataStatsService, useClass: MockMetadataStatsService },
          ],
        },
      ],
    });
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should render top heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
    expect(heading).toHaveTextContent('The German Human Genome‑Phenome Archive');
    expect(heading).toHaveTextContent('Data Portal');
  });

  it('should link to the metadata browser', () => {
    expect(screen.getByRole('link', { name: 'Browse data' })).toHaveAttribute(
      'href',
      '/browse',
    );
  });

  it('should show the global statistics', () => {
    expect(screen.getByRole('heading', { name: 'Statistics' })).toBeInTheDocument();
    expect(screen.getByText('252')).toBeInTheDocument();
  });
});
