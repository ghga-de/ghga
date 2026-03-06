/**
 * Test the Upload Box Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
// eslint-disable-next-line boundaries/element-types
import { uploadBoxes } from '@app/../mocks/data';
import { NotificationService } from '@app/shared/services/notification';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxManagerListComponent } from './upload-box-manager-list';

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

const notifyMock = {
  showError: vitest.fn(),
};

describe('UploadBoxManagerListComponent', () => {
  let component: UploadBoxManagerListComponent;
  let fixture: ComponentFixture<UploadBoxManagerListComponent>;
  let uploadBoxService: MockUploadBoxService;

  beforeEach(async () => {
    notifyMock.showError.mockClear();

    await TestBed.configureTestingModule({
      imports: [UploadBoxManagerListComponent],
      providers: [
        { provide: UploadBoxService, useClass: MockUploadBoxService },
        { provide: NotificationService, useValue: notifyMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(UploadBoxManagerListComponent);
    uploadBoxService = TestBed.inject(
      UploadBoxService,
    ) as unknown as MockUploadBoxService;
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show upload box titles', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Upload Box of John');
  });

  it('should show storage location labels instead of aliases', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('Tübingen 1');
    expect(text).toContain('Heidelberg 2');
  });

  it('should show an error message when upload boxes cannot be loaded', async () => {
    uploadBoxService.setError(new Error('backend unavailable'));
    fixture.detectChanges();
    await fixture.whenStable();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain(
      'There was an error retrieving upload boxes.',
    );
  });

  it('should show a snackbar error notification when upload boxes cannot be loaded', async () => {
    uploadBoxService.setError(new Error('backend unavailable'));
    fixture.detectChanges();
    await fixture.whenStable();

    expect(notifyMock.showError).toHaveBeenCalledWith('Error retrieving upload boxes.');
  });
});
