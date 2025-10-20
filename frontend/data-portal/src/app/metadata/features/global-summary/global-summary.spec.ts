/**
 * Test the global stats component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

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
  let component: GlobalSummaryComponent;
  let fixture: ComponentFixture<GlobalSummaryComponent>;

  beforeEach(async () => {
    await TestBed.overrideComponent(GlobalSummaryComponent, {
      set: {
        providers: [
          { provide: MetadataStatsService, useClass: MockMetadataStatsService },
        ],
      },
    }).compileComponents();

    fixture = TestBed.createComponent(GlobalSummaryComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  /**
   * Check the text content of a card
   * @param index the number of the card
   * @param expected the text to check for
   */
  function expectCardText(index: number, expected: string): void {
    const compiled = fixture.nativeElement as HTMLElement;
    const cards = compiled.querySelectorAll('mat-card');
    expect(cards.length).toBe(4);
    const card = cards[index];
    const text = card.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(text).toContain(expected);
  }

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should properly show total datasets', () => {
    expectCardText(0, 'Total datasets: 252');
  });

  it('should properly show experiments', () => {
    expectCardText(
      1,
      'Experiments: 1,400 Experiments CountPlatform700 Ilumina test 700 HiSeq test',
    );
  });

  it('should properly show individuals', () => {
    expectCardText(2, 'Individuals: 5,432 Individuals CountSex1,935Female2,358Male');
  });

  it('should properly aggregate file types', () => {
    expectCardText(3, 'Files: 703 Files CountFile Type462bam212fastq12txt17zip');
  });
});
