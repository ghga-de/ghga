/**
 * Component for data stewards to see details of an access grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, computed, effect, inject, input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { AccessGrantStatusClassPipe } from '@app/access-requests/pipes/access-grant-status-class-pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state-pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type-pipe';
import { IvaService } from '@app/verification-addresses/services/iva';
import { AccessGrantRevocationDialogComponent } from '../access-grant-revocation-dialog/access-grant-revocation-dialog';

/**
 * Access Grant Manager Details component.
 *
 * This component is used to show details of an access grant.
 */
@Component({
  selector: 'app-access-grant-manager-details',
  imports: [
    FormsModule,
    MatCardModule,
    MatIconModule,
    MatInputModule,
    MatButtonModule,
    MatDatepickerModule,
    MatSelectModule,
    MatTooltipModule,
    MatFormFieldModule,
    MatIconModule,
    AccessGrantStatusClassPipe,
    RouterLink,
    DatePipe,
    IvaTypePipe,
    IvaStatePipe,
  ],
  templateUrl: './access-grant-manager-details.html',
})
export class AccessGrantManagerDetailsComponent implements OnInit {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  readonly periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;

  #location = inject(NavigationTrackingService);
  #ars = inject(AccessRequestService);
  #ivaService = inject(IvaService);
  #dialog = inject(MatDialog);
  #notificationService = inject(NotificationService);

  id = input.required<string>();
  showTransition = false;
  isLoading = this.#ars.allAccessGrantsResource.isLoading;

  error = computed(() => {
    const ags = this.#ars.allAccessGrants()?.filter((ag) => ag.id === this.id());
    if (ags.length !== 1) {
      return true;
    } else {
      return false;
    }
  });

  grant = computed(() => {
    const ags = this.#ars.allAccessGrants()?.filter((ag) => ag.id === this.id());
    if (ags.length !== 1) {
      return undefined;
    } else {
      return ags[0];
    }
  });

  hasStarted = computed(() => {
    const grant = this.grant();
    if (grant) {
      return new Date() > new Date(grant.valid_from);
    }
    return false;
  });

  hasEnded = computed(() => {
    const grant = this.grant();
    if (grant) {
      return new Date() > new Date(grant.valid_until);
    }
    return false;
  });

  ar = computed(() => {
    return this.#ars.allAccessRequests.value().filter((ar) => {
      const grant = this.grant();
      if (grant) {
        const isCorrectDataset = ar.dataset_id === grant.dataset_id;
        const isCorrectUser = ar.user_id === grant.user_id;
        return isCorrectDataset && isCorrectUser;
      } else {
        return false;
      }
    });
  });

  #loadUserIvas = effect(() => {
    const grant = this.grant();
    if (grant) {
      this.#ivaService.loadUserIvas(grant.user_id);
    }
  });

  iva = computed(() => {
    const grant = this.grant();
    if (!grant) return undefined;
    const ivaId = grant.iva_id;
    const userIvas = this.#ivaService.userIvas.value();
    return userIvas.find((iva) => iva.id === ivaId);
  });

  sortedLog = computed(() =>
    [
      ...this.ar().flatMap((ar) => [
        { status: 'Access requested', date: ar.request_created },
        {
          status: ar.status === 'allowed' ? 'Access granted' : 'Access denied',
          date: ar.status_changed,
        },
      ]),
      { status: 'Grant created', date: this.grant()?.created ?? null },
      {
        status: 'Grant started',
        date: this.hasStarted() ? (this.grant()?.valid_from ?? null) : null,
      },
      {
        status: 'Grant expired',
        date: this.hasEnded() ? (this.grant()?.valid_until ?? null) : null,
      },
    ].sort((a, b) => Date.parse(a.date!) - Date.parse(b.date!)),
  );

  /**
   * Activates the transition animation and loads the grant.
   */
  ngOnInit(): void {
    this.#ars.loadAllAccessGrants();
    this.#ars.loadAllAccessRequests();
    this.showTransition = true;
    setTimeout(() => (this.showTransition = false), 300);
  }

  /**
   * Navigate back to the Access Grant Manager.
   */
  goBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/access-grant-manager']);
    });
  }

  /**
   * Revoke the grant.
   */
  #revoke(): void {
    const id = this.grant()?.id;
    if (!id) return;
    this.#ars.revokeAccessGrant(id).subscribe({
      next: () => {
        this.#notificationService.showSuccess(`Access grant was successfully revoked.`);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Access grant could not be revoked. Please try again later',
        );
      },
    });
  }

  /**
   * Revoke the grant after confirmation.
   */
  safeRevoke(): void {
    const dialogRef = this.#dialog.open(AccessGrantRevocationDialogComponent, {
      data: {
        grant: this.grant()!,
      },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) this.#revoke();
    });
  }
}
