/**
 * Component for data stewards to see details of an upload grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  OnInit,
  signal,
} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { IvaStatePipe } from '@app/ivas/pipes/iva-state-pipe';
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { IvaService } from '@app/ivas/services/iva';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { ResearchDataUploadBox, UploadBoxStateClass } from '@app/upload/models/box';
import { UploadBoxService } from '@app/upload/services/upload-box';
import { UploadGrantRevocationDialogComponent } from '../upload-grant-revocation-dialog/upload-grant-revocation-dialog';

/**
 * Upload Grant Manager Details component.
 *
 * This component is used to show details of an upload grant.
 */
@Component({
  selector: 'app-upload-grant-manager-details',
  imports: [
    MatCardModule,
    MatIconModule,
    MatButtonModule,
    MatTooltipModule,
    RouterLink,
    DatePipe,
    IvaTypePipe,
    IvaStatePipe,
    ExternalLinkDirective,
  ],
  templateUrl: './upload-grant-manager-details.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadGrantManagerDetailsComponent implements OnInit {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;
  readonly stateClass = UploadBoxStateClass;

  #location = inject(NavigationTrackingService);
  #uploadBoxService = inject(UploadBoxService);
  #ivaService = inject(IvaService);
  #dialog = inject(MatDialog);

  /** Route parameter: the upload box ID. */
  boxId = input.required<string>();

  /** Route parameter: the upload grant ID. */
  grantId = input.required<string>();

  /** Whether to apply the view transition animation. */
  showTransition = false;

  #cachedBox = signal<ResearchDataUploadBox | undefined>(undefined);

  /** The upload grant being displayed. */
  grant = computed(() => {
    const grants = this.#uploadBoxService.boxGrants.value();
    return grants.find((g) => g.id === this.grantId());
  });

  /** Whether the component data is still loading. */
  isLoading = computed(
    () =>
      this.#uploadBoxService.boxGrants.isLoading() ||
      (!this.#cachedBox() && this.#uploadBoxService.uploadBox.isLoading()),
  );

  /** The upload box associated with this grant. */
  box = computed<ResearchDataUploadBox | undefined>(
    () =>
      this.#cachedBox() ||
      (this.#uploadBoxService.uploadBox.error()
        ? undefined
        : this.#uploadBoxService.uploadBox.value()),
  );

  /** Whether the grant's validity period is currently active. */
  isActive = computed(() => {
    const grant = this.grant();
    if (!grant) return false;
    const today = new Date().toISOString().slice(0, 10);
    return grant.valid_from <= today && today <= grant.valid_until;
  });

  /** Whether the grant's validity period has started. */
  hasStarted = computed(() => {
    const grant = this.grant();
    if (!grant) return false;
    return new Date() >= new Date(grant.valid_from);
  });

  /** Whether the grant's validity period has ended. */
  hasEnded = computed(() => {
    const grant = this.grant();
    if (!grant) return false;
    return new Date() > new Date(grant.valid_until);
  });

  #loadUserIvas = effect(() => {
    const grant = this.grant();
    if (grant) {
      this.#ivaService.loadUserIvas(grant.user_id);
    }
  });

  /** The IVA referenced by this grant, if any. */
  iva = computed(() => {
    const grant = this.grant();
    if (!grant?.iva_id) return undefined;
    const userIvas = this.#ivaService.userIvas.value();
    return userIvas.find((iva) => iva.id === grant.iva_id);
  });

  /** Audit log entries sorted ascending by date. */
  sortedLog = computed(() => {
    const grant = this.grant();
    return [
      { status: 'Grant created', date: grant?.created ?? null },
      {
        status: 'Grant started',
        date: this.hasStarted() ? (grant?.valid_from ?? null) : null,
      },
      {
        status: 'Grant expired',
        date: this.hasEnded() ? (grant?.valid_until ?? null) : null,
      },
    ]
      .filter((item) => item.date !== null)
      .sort((a, b) => Date.parse(a.date!) - Date.parse(b.date!));
  });

  /**
   * Activates the transition animation and loads grant and box data.
   */
  ngOnInit(): void {
    this.showTransition = true;
    setTimeout(() => (this.showTransition = false), 300);

    const boxId = this.boxId();
    if (boxId) {
      this.#uploadBoxService.loadBoxGrants(boxId);
      const single = this.#uploadBoxService.uploadBox.error()
        ? undefined
        : this.#uploadBoxService.uploadBox.value();
      if (single && single.id === boxId) {
        this.#cachedBox.set(single);
      } else {
        const fromList = this.#uploadBoxService
          .uploadBoxes()
          .find((b) => b.id === boxId);
        if (fromList) {
          this.#cachedBox.set(fromList);
        } else {
          this.#uploadBoxService.loadUploadBox(boxId);
        }
      }
    }
  }

  /**
   * Navigate back to the upload box detail page.
   */
  goBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/upload-box-manager', this.boxId()]);
    });
  }

  /**
   * Open the confirmation dialog and revoke the upload grant if confirmed.
   */
  revokeGrant(): void {
    const grant = this.grant();
    if (!grant) return;
    this.#dialog.open(UploadGrantRevocationDialogComponent, {
      data: { grant, boxTitle: this.box()?.title, boxState: this.box()?.state },
    });
  }
}
