/**
 * Test the global stats component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';
import { GlobalSummaryComponent } from './global-summary.component';

import { metadataGlobalSummary } from '@app/../mocks/data';
import { MetadataStatsService } from '@app/metadata/services/metadata-stats.service';

/**
 * Mock the metadata service as needed for the global stats
 */
class MockMetadataStatsService {
  globalSummary = signal(metadataGlobalSummary.resource_stats);
  globalSummaryError = signal(undefined);
  globalSummaryIsLoading = signal(false);
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

  it('should show platforms', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('1400');
    expect(text).toContain('Ilumina test');
  });
});
