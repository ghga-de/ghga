/**
 * Dataset details page
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { datasetDetails, datasetInformation } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { DatasetInformationService } from '@app/metadata/services/dataset-information';
import { MetadataService } from '@app/metadata/services/metadata';
import { DatasetDetailsPage } from './dataset-details';

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

import { signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { MockAccessRequestService } from '@app/access-requests/services/access-request.mock-service';
import { AuthService } from '@app/auth/services/auth';
import { IvaService } from '@app/ivas/services/iva';
import { WellKnownValueService } from '@app/metadata/services/well-known-value';
import { ConfigService } from '@app/shared/services/config';
import { screen, within } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

/**
 * Mock a basic version of the auth service
 */
class MockAuthService {
  fullName = () => 'Dr. John Doe';
  email = () => 'doe@home.org';
  roles = () => ['data_steward'];
  roleNames = () => ['Data Steward'];
}

/**
 * Mock the IVA service as needed by the dynamic access request button
 */
class MockIvaService {
  userIvas = { error: signal(undefined), value: signal([]) };
  loadUserIvas = () => undefined;
}

/**
 * Mock a basic version of the well-known value service
 */
class MockWellKnownValueService {
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

describe('DatasetDetailsPage', () => {
  let component: DatasetDetailsPage;
  let fixture: ComponentFixture<DatasetDetailsPage>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DatasetDetailsPage],
      providers: [
        { provide: ConfigService, useClass: MockConfigService },
        { provide: DatasetInformationService, useClass: MockDatasetInformationService },
        { provide: WellKnownValueService, useClass: MockWellKnownValueService },
        { provide: AuthService, useClass: MockAuthService },
        { provide: AccessRequestService, useClass: MockAccessRequestService },
        { provide: IvaService, useClass: MockIvaService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    })
      .overrideComponent(DatasetDetailsPage, {
        set: {
          providers: [{ provide: MetadataService, useClass: MockMetadataService }],
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(DatasetDetailsPage);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('id', datasetDetails.accession);
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show heading', () => {
    const heading = screen.getByRole('heading', { level: 1 });
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

  it('should show a publication without DOI and no DOI line for it', async () => {
    await userEvent.click(screen.getByRole('tab', { name: /Publications/ }));
    await fixture.whenStable();
    const title = await screen.findByText('Test publication without DOI');
    const publication = title.closest('h2')?.parentElement as HTMLElement;
    expect(within(publication).getByText(/Test author/)).toBeInTheDocument();
    expect(within(publication).queryByText('DOI:')).toBeNull();
    expect(within(publication).queryByText('View Publication')).toBeNull();
  });

  it('should show DAC, data use and policy on separate cards', async () => {
    await userEvent.click(screen.getByRole('tab', { name: /Data Access/ }));
    await fixture.whenStable();
    await screen.findByRole('heading', { level: 2, name: 'Data Access Committee' });
    const card = (title: string) =>
      screen
        .getByRole('heading', { level: 2, name: title })
        .closest('mat-card') as HTMLElement;

    const dac = card('Data Access Committee');
    expect(within(dac).getByText('Test DAC')).toBeInTheDocument();
    expect(within(dac).getByText('test[at]test[dot]de')).toBeInTheDocument();

    const dataUse = card('Data Use');
    expect(
      within(dataUse).getByRole('link', { name: /general research use/ }),
    ).toHaveAttribute('href', 'https://purl.obolibrary.org/obo/DUO_0000042');
    const modifiers = within(dataUse).getAllByRole('listitem');
    expect(modifiers.map((item) => item.textContent?.trim())).toEqual([
      'publication required',
      'institution specific restriction',
    ]);

    const dap = card('Data Access Policy');
    expect(within(dap).getByText('DAP 1')).toBeInTheDocument();
    expect(within(dap).getByText(/^Test policy text\./)).toBeInTheDocument();
    expect(
      within(dap).getByRole('link', {
        name: 'Look up policy terms online (new tab)',
      }),
    ).toHaveAttribute('href', 'https://test.com');
  });
});
