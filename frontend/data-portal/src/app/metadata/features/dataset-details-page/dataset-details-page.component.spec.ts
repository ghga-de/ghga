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
  loadDatasetDetails = () => undefined;
}

import { screen } from '@testing-library/angular';

/**
 * Mock the dataset information service as needed for the dataset details
 */
class MockDatasetInformationService {
  datasetInformation = signal(datasetInformation);
  datasetInformationError = signal(undefined);
  loadDatasetInformation = () => undefined;
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
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show heading', () => {
    const heading = screen.getByRole('heading', { level: 3 });
    expect(heading).toHaveTextContent('Test dataset');
  });

  it('should show GHGA ID', () => {
    expect(screen.queryAllByText('Dataset ID | GHGAD588887987').length).toBeGreaterThan(
      0,
    );
  });

  it('should show EGA ID', () => {
    expect(screen.queryAllByText('EGA ID | EGAD588887987').length).toBeGreaterThan(0);
  });

  it('should show dataset type', () => {
    expect(screen.queryAllByText('Test Type').length).toBeGreaterThan(0);
  });

  it('should show study type', () => {
    expect(screen.queryAllByText('test genomics').length).toBeGreaterThan(0);
  });

  it('should show dataset description', () => {
    const expected = /^Test dataset with some details for testing\./;
    expect(screen.queryByText(expected)).not.toBeNull();
  });

  it('should show offer option to request access', () => {
    expect(screen.getByText('Request Access')).toBeVisible();
  });
});
