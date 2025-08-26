/**
 * Component for data stewards to see details of an access grant.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { AccessGrantStatusClassPipe } from '@app/access-requests/pipes/access-grant-status-class.pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { NavigationTrackingService } from '@app/shared/services/navigation.service';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';

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
    MatInputModule,
    MatButtonModule,
    MatDatepickerModule,
    MatSelectModule,
    MatFormFieldModule,
    MatIconModule,
    AccessGrantStatusClassPipe,
    RouterLink,
    DatePipe,
  ],
  templateUrl: './access-grant-manager-details.component.html',
  styleUrl: './access-grant-manager-details.component.scss',
})
export class AccessGrantManagerDetailsComponent implements OnInit {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  readonly periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;

  showTransition = false;

  #location = inject(NavigationTrackingService);

  id = input.required<string>();
  #ars = inject(AccessRequestService);

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
}
