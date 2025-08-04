/**
 * Dataset details page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { provideAnimations } from '@angular/platform-browser/animations';
import { datasetDetails, datasetInformation } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { DatasetInformationService } from '@app/metadata/services/dataset-information.service';
import { MetadataService } from '@app/metadata/services/metadata.service';
import { DatasetDetailsComponent } from './dataset-details.component';

/**
 * Mock the config service as needed by the dataset details component
 */
class MockConfigService {
  rtsUrl = 'http://mock.dev/rts';
}

/**
 * Mock the metadata service as needed for the dataset details
 */
class MockMetadataService {
  datasetDetails = {
    value: () => datasetDetails,
    isLoading: () => false,
    error: () => undefined,
  };
  loadDatasetDetails = () => undefined;
}

import { ActivatedRoute } from '@angular/router';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { AuthService } from '@app/auth/services/auth.service';
import { WellKnownValueService } from '@app/metadata/services/well-known-value.service';
import { ConfigService } from '@app/shared/services/config.service';
import { screen } from '@testing-library/angular';

/**
 * Mock a basic version of the auth service
 */
export class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

/**
 * Mock a basic version of the well-known value service
 */
export class MockWellKnownValueService {
  storageLabels = {
    value: () => ({ storage_labels: { TUE01: 'Tübingen', TUE02: 'Tübingen' } }),
    isLoading: () => false,
    error: () => undefined,
  };
}

/**
 * Mock the dataset information service as needed for the dataset details
 */
class MockDatasetInformationService {
  datasetInformation = {
    value: () => datasetInformation,
    isLoading: () => false,
    error: () => undefined,
  };
  loadDatasetInformation = () => undefined;
}

describe('DatasetDetailsComponent', () => {
  let component: DatasetDetailsComponent;
  let fixture: ComponentFixture<DatasetDetailsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetDetailsComponent],
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
        { provide: DatasetInformationService, useClass: MockDatasetInformationService },
        { provide: WellKnownValueService, useClass: MockWellKnownValueService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
        provideAnimations(),
      ],
    })
      .overrideComponent(DatasetDetailsComponent, {
        set: {
          providers: [{ provide: MetadataService, useClass: MockMetadataService }],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(DatasetDetailsComponent);
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
    expect(
      screen.queryAllByText('Dataset ID | GHGAD12345678901234').length,
    ).toBeGreaterThan(0);
  });

  it('should show EGA ID', () => {
    expect(screen.queryAllByText('EGA ID | EGAD12345678901').length).toBeGreaterThan(0);
  });

  it('should show dataset type', () => {
    expect(
      screen.queryAllByText(
        'Test Type Lorem ipsum dolor sit amet, consectetur adipiscing elit',
      ).length,
    ).toBeGreaterThan(0);
  });

  it('should show study type', () => {
    expect(
      screen.queryAllByText(
        'test genomics Lorem ipsum dolor sit amet, consectetur adipiscing elit',
      ).length,
    ).toBeGreaterThan(0);
  });

  it('should show dataset description', () => {
    const expected = /^Test dataset with some details for testing\./;
    expect(screen.queryByText(expected)).not.toBeNull();
  });
});
