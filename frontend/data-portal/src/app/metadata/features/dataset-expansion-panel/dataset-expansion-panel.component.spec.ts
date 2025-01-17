/**
 * Test the dataset expansion panel
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';

import { datasetSummary, searchResults } from '@app/../mocks/data';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { DatasetExpansionPanelComponent } from './dataset-expansion-panel.component';

/**
 * Mock the metadata service as needed for the dataset summary
 */
class MockMetadataService {
  datasetSummary = signal(datasetSummary);
  datasetSummaryError = signal(undefined);
}

describe('DatasetExpansionPanelComponent', () => {
  let component: DatasetExpansionPanelComponent;
  let fixture: ComponentFixture<DatasetExpansionPanelComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetExpansionPanelComponent],
      providers: [{ provide: MetadataService, useClass: MockMetadataService }],
    }).compileComponents();

    fixture = TestBed.createComponent(DatasetExpansionPanelComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('hit', searchResults.hits.at(0));
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show datasets', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('GHGAD588887987');
    expect(text).toContain('Test dataset for details');
  });
});
