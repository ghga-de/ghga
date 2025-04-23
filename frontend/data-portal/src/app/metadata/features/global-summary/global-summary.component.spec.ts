/**
 * Test the global stats component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GlobalSummaryComponent } from './global-summary.component';

import { metadataGlobalSummary } from '@app/../mocks/data';
import { MetadataStatsService } from '@app/metadata/services/metadata-stats.service';

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

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show methods', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('700');
    expect(text).toContain('Ilumina test');
  });
});
