/**
 * Component that hosts the Upload Box Manager feature.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ChangeDetectionStrategy, Component, inject, OnInit } from '@angular/core';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadBoxManagerFilterComponent } from '../upload-box-manager-filter/upload-box-manager-filter';
import { UploadBoxManagerListComponent } from '../upload-box-manager-list/upload-box-manager-list';

/**
 * Upload Box Manager component.
 *
 * This component is the data steward entry point for upload box management.
 */
@Component({
  selector: 'app-upload-box-manager',
  imports: [UploadBoxManagerFilterComponent, UploadBoxManagerListComponent],
  templateUrl: './upload-box-manager.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadBoxManagerComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);

  /**
   * Load all upload boxes when the component is initialized.
   */
  ngOnInit(): void {
    this.#uploadBoxService.loadAllUploadBoxes();
  }
}
