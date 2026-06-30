/**
 * Tests for the upload box mapping confirmation dialog component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import {
  MappingConfirmDialogData,
  UploadBoxMappingConfirmDialogComponent,
} from './upload-box-mapping-confirm-dialog';

const mockDialogRef = { close: vitest.fn() };

describe('UploadBoxMappingConfirmDialogComponent', () => {
  let fixture: ComponentFixture<UploadBoxMappingConfirmDialogComponent>;

  /**
   * Creates the dialog component with the given input data.
   * @param data - dialog data used to configure confirmation behavior
   * @returns a promise that resolves once the fixture is stable
   */
  async function createComponent(data: MappingConfirmDialogData): Promise<void> {
    await TestBed.configureTestingModule({
      imports: [UploadBoxMappingConfirmDialogComponent],
      providers: [
        { provide: MatDialogRef, useValue: mockDialogRef },
        { provide: MAT_DIALOG_DATA, useValue: data },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxMappingConfirmDialogComponent);
    fixture.detectChanges();
    await fixture.whenStable();
  }

  beforeEach(() => {
    mockDialogRef.close.mockReset();
    TestBed.resetTestingModule();
  });

  it('should block confirmation when upload-box files are still unmapped', async () => {
    await createComponent({
      unmappedBoxFileAliases: ['unmapped.fastq.gz'],
      unmappedMetaFileNames: ['metadata.fastq.gz'],
    });

    expect(
      screen.getByText(/the following file in the upload box has not been mapped/i),
    ).toBeVisible();
    expect(
      screen.queryByRole('button', { name: /confirm and archive/i }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
  });

  it('should keep confirm disabled until the acknowledgement checkbox is ticked', async () => {
    await createComponent({
      unmappedBoxFileAliases: [],
      unmappedMetaFileNames: ['metadata.fastq.gz'],
    });

    const confirmButton = screen.getByRole('button', { name: /confirm and archive/i });
    const checkbox = screen.getByRole('checkbox', {
      name: /i understand this action cannot be undone/i,
    });

    expect(confirmButton).toBeDisabled();

    await userEvent.click(checkbox);
    fixture.detectChanges();

    expect(confirmButton).toBeEnabled();
  });

  it('should close with false when cancel is clicked', async () => {
    await createComponent({
      unmappedBoxFileAliases: [],
      unmappedMetaFileNames: [],
    });

    await userEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(mockDialogRef.close).toHaveBeenCalledWith(false);
  });

  it('should close with true after confirmation is acknowledged and submitted', async () => {
    await createComponent({
      unmappedBoxFileAliases: [],
      unmappedMetaFileNames: [],
    });

    await userEvent.click(
      screen.getByRole('checkbox', {
        name: /i understand this action cannot be undone/i,
      }),
    );
    fixture.detectChanges();
    await userEvent.click(screen.getByRole('button', { name: /confirm and archive/i }));

    expect(mockDialogRef.close).toHaveBeenCalledWith(true);
  });
});
