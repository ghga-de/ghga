/**
 * Test the Upload Box Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { uploadBoxes } from '@app/../mocks/data';
import { Notifier } from '@app/shared/services/notification';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { render, RenderResult, screen, within } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { UploadBoxManagerList } from './upload-box-manager-list';

/**
 * Mock the upload box service as needed by the upload box manager list component.
 */
class MockUploadBoxService {
  #error = signal<Error | undefined>(undefined);

  boxRetrievalResults = {
    value: () => uploadBoxes,
    isLoading: () => false,
    error: this.#error,
  };
  filteredUploadBoxes = () => this.boxRetrievalResults.value().boxes;
  getStorageLocationLabel = (storageAlias: string) =>
    ({ TUE01: 'Tübingen 1', HD02: 'Heidelberg 2', TUE03: 'Tübingen 3' })[
      storageAlias
    ] ?? storageAlias;

  /**
   * Set retrieval error for tests.
   * @param error - retrieval error to expose
   */
  setError(error: Error | undefined): void {
    this.#error.set(error);
  }
}

/**
 * Stand-in for the upload box details page the list navigates to
 */
@Component({ template: '' })
class UploadBoxDetailsStubComponent {}

const notifyMock = {
  showError: vitest.fn(),
};

describe('UploadBoxManagerList', () => {
  let result: RenderResult<UploadBoxManagerList>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    notifyMock.showError.mockClear();

    result = await render(UploadBoxManagerList, {
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: Notifier, useValue: notifyMock },
      ],
      routes: [
        { path: 'upload-box-manager/:id', component: UploadBoxDetailsStubComponent },
      ],
    });
    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
  });

  it('should create', () => {
    expect(result.fixture.componentInstance).toBeTruthy();
  });

  it('should show upload box titles', () => {
    expect(screen.getByText('Research Data Upload Box of John')).toBeVisible();
  });

  it('should show storage location labels instead of aliases', () => {
    expect(screen.getByText('Tübingen 1')).toBeVisible();
    expect(screen.getAllByText('Heidelberg 2')).toHaveLength(3);
    expect(screen.queryByText('TUE01')).not.toBeInTheDocument();
  });

  it('should navigate to the details of an upload box', async () => {
    const box = uploadBoxes.boxes[0];
    const row = screen.getByRole('row', { name: new RegExp(box.title) });
    await userEvent.click(
      within(row).getByRole('button', { name: 'View upload box details' }),
    );
    await result.fixture.whenStable();
    expect(TestBed.inject(Router).url).toBe(`/upload-box-manager/${box.id}`);
  });

  it('should show an error message when upload boxes cannot be loaded', async () => {
    expect(screen.queryByText(/error retrieving upload boxes/)).toBeNull();

    uploadBoxService.setError(new Error('backend unavailable'));
    await result.fixture.whenStable();

    expect(
      screen.getByText(/There was an error retrieving upload boxes\./),
    ).toBeVisible();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('should show a snackbar error notification when upload boxes cannot be loaded', async () => {
    uploadBoxService.setError(new Error('backend unavailable'));
    await result.fixture.whenStable();

    expect(notifyMock.showError).toHaveBeenCalledWith('Error retrieving upload boxes.');
  });
});
