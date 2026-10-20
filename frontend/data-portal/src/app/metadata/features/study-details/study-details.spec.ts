/**
 * Test the study details component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { render, RenderResult, screen, within } from '@testing-library/angular';

import { searchResults, studyData } from '@app/../mocks/data';
import { MetadataService } from '@app/metadata/services/metadata';
import { ConfigService } from '@app/shared/services/config';
import { StudyDetails } from './study-details';

/**
 * Mock the metadata service as needed for the study details
 */
class MockMetadataService {
  study = {
    value: () => studyData,
    isLoading: () => false,
    error: () => undefined,
    hasValue: () => true,
  };
  loadStudy = vitest.fn();
}

const mockConfig = {
  massUrl: '/test/mass',
  rtsUrl: '/test/rts',
};

const STUDY_ID = studyData.accession;

const DATASETS_URL =
  '/test/mass/search?class_name=EmbeddedDataset' +
  `&filter_by=study.accession&value=${STUDY_ID}&limit=100`;

describe('StudyDetails', () => {
  let result: RenderResult<StudyDetails>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    result = await render(StudyDetails, {
      inputs: { id: STUDY_ID },
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ConfigService, useValue: mockConfig },
      ],
      configureTestBed: (testBed) =>
        testBed.overrideComponent(StudyDetails, {
          set: {
            providers: [{ provide: MetadataService, useClass: MockMetadataService }],
          },
        }),
      routes: [],
    });
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  /**
   * Answer the request for the datasets of the study
   * @param hits the datasets to respond with
   */
  async function flushDatasets(hits = searchResults.hits.slice(0, 2)): Promise<void> {
    httpMock.expectOne(DATASETS_URL).flush({ hits, count: hits.length });
    await result.fixture.whenStable();
  }

  it('should create', async () => {
    expect(result.fixture.componentInstance).toBeTruthy();
    await flushDatasets();
  });

  it('should load the study with the given id', async () => {
    const metadata = result.debugElement.injector.get(MetadataService);
    expect(metadata.loadStudy).toHaveBeenCalledWith(STUDY_ID);
    await flushDatasets();
  });

  it('should show the study details', async () => {
    await flushDatasets();
    expect(
      screen.getByRole('heading', { level: 1, name: 'Study Details' }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: 'Test Study' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Download Metadata/ })).toHaveAttribute(
      'href',
      `/test/rts/studies/${STUDY_ID}`,
    );
  });

  it('should list the datasets of the study', async () => {
    await flushDatasets();
    const table = screen.getByRole('table', {
      name: `Datasets belonging to study ${STUDY_ID}`,
    });
    const link = within(table).getByRole('link', { name: 'GHGAD12345678901235' });
    expect(link).toHaveAttribute('href', '/dataset/GHGAD12345678901235');
    expect(within(table).getAllByRole('row')).toHaveLength(3);
  });
});
