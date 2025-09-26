/**
 * View allowing a data steward to manage an individual access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  model,
  OnInit,
  signal,
  Signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIcon } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { RouterLink } from '@angular/router';
import {
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class-pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { UserSession } from '@app/auth/models/user';
import { HasPendingEdits } from '@app/shared/features/pending-edits';
import { SplitLinesPipe } from '@app/shared/pipes/split-lines-pipe';
import { ConfigService } from '@app/shared/services/config';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { ExternalLinkDirective } from '@app/shared/ui/external-link/external-link';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { Iva, IvaState } from '@app/verification-addresses/models/iva';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state-pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type-pipe';
import { IvaService } from '@app/verification-addresses/services/iva';
import { AccessRequestDurationEditComponent } from '../access-request-duration-edit/access-request-duration-edit';
import { AccessRequestFieldEditComponent } from '../access-request-field-edit/access-request-field-edit';

/**
 * The view component used for managing access requests in the access request manager.
 * Currently, the data steward can only allow or deny requests, and select an IVA.
 */
@Component({
  selector: 'app-access-request-manager-dialog',
  imports: [
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatRadioModule,
    MatIcon,
    DatePipe,
    AccessRequestStatusClassPipe,
    IvaTypePipe,
    IvaStatePipe,
    AccessRequestFieldEditComponent,
    MatChipsModule,
    MatInputModule,
    SplitLinesPipe,
    ExternalLinkDirective,
    RouterLink,
    AccessRequestDurationEditComponent,
  ],
  providers: [IvaTypePipe, DatePipe],
  templateUrl: './access-request-manager-detail.html',
})
export class AccessRequestManagerDetailComponent implements OnInit, HasPendingEdits {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  showTransition = false;
  allowedState = AccessRequestStatus.allowed;
  #config = inject(ConfigService);
  #ivaService = inject(IvaService);
  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(NotificationService);
  #accessRequestService = inject(AccessRequestService);

  #authUrl = this.#config.authUrl;
  #usersUrl = `${this.#authUrl}/users`;

  #location = inject(NavigationTrackingService);

  id = input.required<string>();
  #request = this.#accessRequestService.accessRequest;
  #requests = this.#accessRequestService.allAccessRequests;

  #cachedRequest = signal<AccessRequest | undefined>(undefined);

  request = computed<AccessRequest | undefined>(
    () =>
      this.#cachedRequest() ||
      (this.#request.error() ? undefined : this.#request.value()),
  );

  loading = computed<boolean>(
    () => !this.#cachedRequest() && this.#request.isLoading(),
  );

  error = computed<undefined | 'not found' | 'other'>(() => {
    if (this.#cachedRequest()) return undefined;
    const error = this.#request.error();
    if (!error) return undefined;

    return (this.#request.error() as HttpErrorResponse)?.status === 404
      ? 'not found'
      : 'other';
  });

  #ivas = this.#ivaService.userIvas;
  ivas = this.#ivas.value;
  ivasAreLoading = this.#ivas.isLoading;
  ivasError = this.#ivas.error;

  #ivaTypePipe = inject(IvaTypePipe);
  #datePipe = inject(DatePipe);

  selectedIvaIdRadioButton = model<string | undefined>(undefined);

  #pendingEdits = new Set<keyof AccessRequest>();

  /**
   * Check if there are pending edits (implements the HasPendingEdits interface)
   * @returns true if there are pending edits, false otherwise
   */
  hasPendingEdits(): boolean {
    return this.#pendingEdits.size > 0;
  }

  /**
   * Computed signal for the user ID of the access request
   */
  #userId = computed(() => this.request()?.user_id);

  /**
   * Resource for loading the external ID of the user who made the access request
   * Only loads when userId is set
   */
  userExtId = httpResource<string | undefined>(
    () => {
      const userId = this.#userId();
      if (!userId) return undefined;
      return `${this.#usersUrl}/${userId}`;
    },
    {
      parse: (raw) => (raw as UserSession).ext_id,
      defaultValue: undefined,
    },
  );

  /**
   * Get the IVA associated with the access request.
   */
  associatedIva: Signal<Iva | undefined> = computed(() => {
    const ivaId = this.request()?.iva_id;
    return ivaId ? this.ivas().find((iva) => iva.id === ivaId) : undefined;
  });

  /**
   * Check whether the access request is changeable.
   * Currently the backend only allows to changed pending requests.
   */
  changeable: Signal<boolean> = computed(
    () => this.request()?.status === AccessRequestStatus.pending,
  );

  #ivasErrorEffect = effect(() => {
    if (this.ivasError()) {
      this.#notificationService.showError('Error fetching verification addresses.');
    }
  });

  #ivasLoadedEffect = effect(() => {
    if (!this.ivasAreLoading() && !this.ivasError() && this.ivas().length) {
      this.#preSelectIvaRadioButton();
    }
  });

  /**
   * Get the display name for the IVA type
   * @param iva the IVA in question
   * @returns the display name for the type
   */
  #ivaTypeName(iva: Iva): string {
    return this.#ivaTypePipe.transform(iva.type).name;
  }

  /**
   * Load the IVAs of the user when the component is initialized
   */
  #loadUserIvasEffect = effect(() => {
    const userId = this.#userId();
    if (userId) {
      this.#ivaService.loadUserIvas(userId);
    }
  });

  /**
   * On initialization, fetch the access request if needed
   */
  ngOnInit(): void {
    this.showTransition = true;
    setTimeout(() => (this.showTransition = false), 300);
    const id = this.id();
    if (id) {
      // Has it been fetched individually already?
      let ar = this.#request.error() ? undefined : this.#request.value();
      if (ar && ar.id === id) {
        this.#cachedRequest.set(ar);
      } else {
        // Has it been fetched as part of a list?
        const requests = this.#requests.error() ? [] : this.#requests.value();
        ar = requests.find((ar: AccessRequest) => ar.id === id);
        if (ar) {
          this.#cachedRequest.set(ar);
        } else {
          // If not, we need to fetch it now
          this.#accessRequestService.loadAccessRequest(id);
        }
      }
    }
  }

  /**
   * Navigate back to the last page (usually the access request manager)
   */
  goBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/access-request-manager']);
    });
  }

  /**
   * Update the request.
   * @param changes - The changes to apply
   */
  #update(changes: Partial<AccessRequest>): void {
    const id = this.request()?.id;
    if (!id) return;
    this.#accessRequestService.updateRequest(id, changes).subscribe({
      next: () => {
        this.#notificationService.showSuccess(
          `Access request was successfully modified.`,
        );
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'Access request could not be modified. Please try again later',
        );
      },
    });
  }

  /**
   * Memorize which editors have changes.
   * @param event - The name of the fields and whether they were edited
   */
  edited(event: [keyof AccessRequest, boolean]): void {
    const [name, edited] = event;
    if (edited) this.#pendingEdits.add(name);
    else this.#pendingEdits.delete(name);
  }

  /**
   * Save field changes.
   * @param event - The names of the field and their new values
   */
  saved(event: Map<keyof AccessRequest, string>): void {
    const data = Object.fromEntries(event);
    this.#update(data as Partial<AccessRequest>);
  }

  /**
   * Update the IVA selection.
   */
  saveIva() {
    this.#update({ iva_id: this.selectedIvaIdRadioButton() });
  }

  /**
   * Allow the access request after confirmation.
   */
  safeAllow(): void {
    const request = this.request();
    if (!request || !this.selectedIvaIdRadioButton()) return;
    const iva = this.ivas().find((iva) => iva.id === this.selectedIvaIdRadioButton());
    if (!iva) return;
    const ivaType = this.#ivaTypeName(iva);
    const startDate = this.#datePipe.transform(
      request.access_starts,
      this.friendlyDateFormat,
    );
    const startDateInFuture = new Date(request.access_starts) > new Date();
    const endDate = this.#datePipe.transform(
      request.access_ends,
      this.friendlyDateFormat,
    );
    this.#confirmationService.confirm({
      title: 'Confirm approval of the access request',
      message:
        '<p>Please confirm that the access request shall be <strong>allowed</strong>' +
        (startDateInFuture
          ? ` for the period between <strong>${startDate}</strong> and`
          : ` until`) +
        ` <strong>${endDate}</strong>, and coupled to the address ${ivaType}: ${iva.value}.` +
        `</p><p><strong>Once allowed, no further changes can be made to the access request!</strong></p>`,
      cancelText: 'Cancel',
      confirmText: 'Confirm allowance',
      confirmClass: 'success',
      callback: (approvalConfirmed) => {
        if (approvalConfirmed) this.#allowAndGoBack();
      },
    });
  }

  /**
   * Deny the access request after confirmation.
   */
  safeDeny(): void {
    this.#confirmationService.confirm({
      title: 'Confirm denial of the access request',
      message:
        '<p>Please confirm that the access request shall be <strong>denied</strong>.' +
        `</p><p><strong>Once denied, no further changes can be made to the access request!</strong></p>`,
      cancelText: 'Cancel',
      confirmText: 'Confirm denial',
      confirmClass: 'error',
      callback: (denialConfirmed) => {
        if (denialConfirmed) this.#denyAndGoBack();
      },
    });
  }

  /**
   * Checks if the user has pending changes before proceeding with a status change.
   * If there are unsaved edits, prompts the user to confirm discarding them before proceeding.
   * @param action String literal specifying the desired status change.
   */
  saveBeforeStatusChange(action: 'deny' | 'allow'): void {
    if (this.hasPendingEdits()) {
      this.#confirmationService.confirm({
        title: 'Unsaved changes',
        message: 'Do you want to continue without saving your changes?',
        cancelText: 'Cancel',
        confirmText: 'Discard Changes',
        confirmClass: 'danger',
        callback: (wantsToDiscard) => {
          if (wantsToDiscard) {
            if (action === 'allow') this.safeAllow();
            else this.safeDeny();
          }
        },
      });
    } else {
      if (action === 'allow') this.safeAllow();
      else this.safeDeny();
    }
  }

  /**
   * Allow the access request and go back to the last page.
   */
  #allowAndGoBack = () => {
    if (!this.selectedIvaIdRadioButton()) return;
    this.#update({
      iva_id: this.selectedIvaIdRadioButton(),
      status: AccessRequestStatus.allowed,
    });
    this.goBack();
  };

  /**
   * Deny the access request and go back to the last page.
   */
  #denyAndGoBack = () => {
    this.#update({
      status: AccessRequestStatus.denied,
    });
    this.goBack();
  };

  /**
   * Pre-select the radio button for the IVA that best matches
   * (the IVA that is already selected or the best option otherwise)
   */
  #preSelectIvaRadioButton(): void {
    const ivaId = this.request()?.iva_id;
    this.selectedIvaIdRadioButton.set(ivaId || this.#findBestIvaId());
  }

  /**
   * Get the "best" IVA for a changeable access request.
   * @returns The ID of the IVA closest to being verified and latest.
   */
  #findBestIvaId(): string | undefined {
    let bestRank: number | undefined = undefined;
    let lastChanged: string | undefined = undefined;
    let ivaId: string | undefined;
    for (const iva of this.ivas()) {
      const rank = {
        [IvaState.Verified]: 1,
        [IvaState.CodeTransmitted]: 2,
        [IvaState.CodeCreated]: 3,
        [IvaState.CodeRequested]: 4,
        [IvaState.Unverified]: 5,
      }[iva.state];
      const changed = iva.changed;
      if (!bestRank || rank < bestRank) {
        bestRank = rank;
        lastChanged = changed;
        ivaId = iva.id;
      } else if (rank === bestRank && (!lastChanged || changed > lastChanged)) {
        lastChanged = changed;
        ivaId = iva.id;
      }
    }
    return ivaId;
  }
}
