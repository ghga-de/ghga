/**
 * Dataset details page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { signal } from '@angular/core';
import { provideAnimations } from '@angular/platform-browser/animations';
import { datasetDetails, datasetInformation } from '@app/../mocks/data';
import { DatasetInformationService } from '@app/metadata/services/dataset-information.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { DatasetDetailsPageComponent } from './dataset-details-page.component';

/**
 * Mock the metadata service as needed for the dataset details
 */
class MockMetadataService {
  datasetDetails = signal(datasetDetails);
  datasetDetailsError = signal(undefined);
  loadDatasetDetailsID = () => undefined;
}

/**
 * Mock the dataset information service as needed for the dataset details
 */
class MockDatasetInformationService {
  datasetInformation = signal(datasetInformation);
  datasetInformationError = signal(undefined);
  loadDatasetID = () => undefined;
}

describe('DatasetDetailsPageComponent', () => {
  let component: DatasetDetailsPageComponent;
  let fixture: ComponentFixture<DatasetDetailsPageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetDetailsPageComponent],
      providers: [
        { provide: MetadataService, useClass: MockMetadataService },
        { provide: DatasetInformationService, useClass: MockDatasetInformationService },
        provideAnimations(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(DatasetDetailsPageComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('id', datasetDetails.accession);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show details', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Test Type');
    expect(text).toContain(
      'Test dataset for Metadata Repository get dataset details call.',
    );
  });
});
