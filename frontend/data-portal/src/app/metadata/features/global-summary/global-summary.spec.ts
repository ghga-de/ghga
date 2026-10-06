/**
 * Test the global stats component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { render, RenderResult, screen } from '@testing-library/angular';

import { GlobalSummaryComponent } from './global-summary';

import { metadataGlobalSummary } from '@app/../mocks/data';
import { MetadataStatsService } from '@app/metadata/services/metadata-stats';

/**
 * Mock the metadata service as needed for the global stats
 */
class MockMetadataStatsService {
  globalSummary = {
    value: () => metadataGlobalSummary.resource_stats,
    isLoading: () => false,
    error: () => undefined,
  };
}

describe('GlobalStatsComponent', () => {
  let result: RenderResult<GlobalSummaryComponent>;

  beforeEach(async () => {
    result = await render(GlobalSummaryComponent, {
      configureTestBed: (testBed) =>
        testBed.overrideComponent(GlobalSummaryComponent, {
          set: {
            providers: [
              { provide: MetadataStatsService, useClass: MockMetadataStatsService },
            ],
          },
        }),
    });
  });

  /**
   * Check the text content of the card with the given title
   * @param title the start of the card title
   * @param expected the text to check for
   */
  function expectCardText(title: string, expected: string): void {
    const card = screen.getByText(title, { exact: false }).closest('mat-card');
    expect(card).not.toBeNull();
    const text = card!.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(text).toContain(expected);
  }

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show the statistics with a table for three of the cards', () => {
    expect(screen.getByRole('heading', { name: 'Statistics' })).toBeInTheDocument();
    expect(screen.getAllByRole('table')).toHaveLength(3);
    for (const name of ['Experiments', 'Individuals', 'Files']) {
      expect(screen.getByRole('table', { name })).toBeInTheDocument();
    }
  });

  it('should properly show total datasets', () => {
    expectCardText('Total datasets:', 'Total datasets: 252');
  });

  it('should properly show experiments', () => {
    expectCardText(
      'Experiments:',
      'Experiments: 1,400 ExperimentsCountPlatform150HiSeq test50Illumina test 6002',
    );
  });

  it('should properly show individuals', () => {
    expectCardText(
      'Individuals:',
      'Individuals: 5,432 IndividualsCountSex1,935Female2,358Male',
    );
  });

  it('should properly aggregate file types', () => {
    expectCardText('Files:', 'Files: 703 FilesCountFile Type462bam212fastq12txt17zip');
  });
});
