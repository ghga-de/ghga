/**
 * View allowing a data steward to manage an individual access request.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import {
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  OnInit,
  signal,
  Signal,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { form, FormField } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIcon } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { RouterLink } from '@angular/router';
import {
  AccessGrant,
  AccessGrantStateLabel,
  AccessGrantStatus,
  AccessRequest,
  AccessRequestStatus,
} from '@app/access-requests/models/access-requests';
import { AccessGrantStatusClassPipe } from '@app/access-requests/pipes/access-grant-status-class-pipe';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class-pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { UserRegisteredData } from '@app/auth/models/user';
import { Iva, IvaState } from '@app/ivas/models/iva';
import { IvaStatePipe } from '@app/ivas/pipes/iva-state-pipe';
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { IvaService } from '@app/ivas/services/iva';
import { HasPendingEdits } from '@app/shared/features/pending-edits';
import { DatePipe } from '@app/shared/pipes/date-pipe';
import { SplitLinesPipe } from '@app/shared/pipes/split-lines-pipe';
import { ConfigService } from '@app/shared/services/config';
import { ConfirmationService } from '@app/shared/services/confirmation';
import { NavigationTracker } from '@app/shared/services/navigation';
import { Notifier } from '@app/shared/services/notification';
import { ExternalLink } from '@app/shared/ui/external-link/external-link';
import {
  DEFAULT_DATE_OUTPUT_FORMAT,
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { html } from '@app/shared/utils/html';
import { AccessRequestDurationEdit } from '../access-request-duration-edit/access-request-duration-edit';
import { interval, map } from 'rxjs';
import { AccessRequestFieldEdit } from '../access-request-field-edit/access-request-field-edit';

const DAY_MS = 24 * 60 * 60 * 1000;

/**
 * The view component used for managing access requests in the access request manager.
 * Currently, the data steward can only allow or deny requests, and select an IVA.
 */
@Component({
  selector: 'app-access-request-manager-dialog',
  imports: [
    FormField,
    MatCardModule,
    MatButtonModule,
    MatRadioModule,
    MatIcon,
    DatePipe,
    AccessRequestStatusClassPipe,
    AccessGrantStatusClassPipe,
    IvaTypePipe,
    IvaStatePipe,
    AccessRequestFieldEdit,
    MatChipsModule,
    MatInputModule,
    SplitLinesPipe,
    ExternalLink,
    RouterLink,
    AccessRequestDurationEdit,
  ],
  providers: [IvaTypePipe, CommonDatePipe],
  templateUrl: './access-request-manager-detail.html',
})
export class AccessRequestManagerDetail implements OnInit, HasPendingEdits {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  readonly periodFormat = DEFAULT_DATE_OUTPUT_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;
  readonly accessLabels = AccessGrantStateLabel;
  showTransition = signal(false);
  allowedState = AccessRequestStatus.allowed;
  #config = inject(ConfigService);
  #ivaService = inject(IvaService);
  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(Notifier);
  #accessRequestService = inject(AccessRequestService);

  #authUrl = this.#config.authUrl;
  #usersUrl = `${this.#authUrl}/users`;

  #location = inject(NavigationTracker);

  protected readonly minDays = this.#config.accessGrantMinDays;
  private durationEdit = viewChild(AccessRequestDurationEdit);

  /**
   * The current time, ticking every minute, so the period warning keeps up with it.
   */
  #now = toSignal(interval(60_000).pipe(map(() => Date.now())), {
    initialValue: Date.now(),
  });

  id = input.required<string>();
  #request = this.#accessRequestService.accessRequest;
  #requests = this.#accessRequestService.allAccessRequests;

  #cachedRequest = signal<AccessRequest | undefined>(undefined);

  request = computed<AccessRequest | undefined>(
    () =>
      this.#cachedRequest() ||
      (this.#request.error() ? undefined : this.#request.value()),
  );

  isLoading = computed<boolean>(
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

  #grantsResource = this.#accessRequestService.allAccessGrantsResource;
  grantsAreLoading = this.#grantsResource.isLoading;
  grantsError = this.#grantsResource.error;

  /**
   * Load all access grants once a request is available, so the corresponding
   * grants (same user and dataset) and their current states can be shown.
   */
  #loadGrantsEffect = effect(() => {
    if (this.request()) this.#accessRequestService.loadAllAccessGrants();
  });

  /**
   * The access grants corresponding to this request (same user and dataset),
   * ordered by creation date. Empty if there are no matching grants.
   */
  grants = computed<AccessGrant[]>(() => {
    const ar = this.request();
    return ar ? this.#accessRequestService.grantsFor(ar.user_id, ar.dataset_id) : [];
  });

  /**
   * The aggregated current access state across all corresponding grants
   * (undefined if there are no matching grants). This is the same live state
   * shown in the access request manager's "Access" column.
   */
  grantState = computed<AccessGrantStatus | undefined>(() => {
    const ar = this.request();
    return ar
      ? this.#accessRequestService.grantStateFor(ar.user_id, ar.dataset_id)
      : undefined;
  });

  #ivaTypePipe = inject(IvaTypePipe);
  #datePipe = inject(CommonDatePipe);

  /**
   * The IVA selected in the radio group. Whenever the IVAs have loaded, it is
   * preset to the IVA of the request or to the best IVA of the user.
   */
  selectedIvaIdRadioButton = linkedSignal<boolean, string | undefined>({
    source: () => !this.ivasAreLoading() && !this.ivasError() && this.ivas().length > 0,
    computation: (loaded, previous) =>
      loaded ? this.request()?.iva_id || this.#findBestIvaId() : previous?.value,
  });

  /**
   * The IVA selection, bound to the radio group
   */
  protected ivaField = form(this.selectedIvaIdRadioButton);

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
   * Resource for loading the user who made the access request,
   * whose LS ID and LS Login email are not part of the request.
   * Only loads when userId is set.
   */
  requester = httpResource<UserRegisteredData | undefined>(
    () => {
      const userId = this.#userId();
      if (!userId) return undefined;
      return `${this.#usersUrl}/${userId}`;
    },
    { defaultValue: undefined },
  );

  /**
   * The external ID with a zero-width space before the `@`, so that it can wrap there.
   */
  protected userExtIdText = computed(() =>
    this.requester.value()?.ext_id.split('@', 2).join('\u200B@'),
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

  /**
   * Whether the access period of a pending request has ended or is shorter than the
   * minimum. A start in the past counts as now, since allowing the request moves it
   * up to now.
   */
  protected periodWarning = computed<'ended' | 'short' | undefined>(() => {
    const ar = this.request();
    if (ar?.status !== AccessRequestStatus.pending) return undefined;
    const now = this.#now();
    const ends = new Date(ar.access_ends).getTime();
    if (ends <= now) return 'ended';
    const starts = Math.max(now, new Date(ar.access_starts).getTime());
    if (ends - starts < this.minDays * DAY_MS) return 'short';
    return undefined;
  });

  /**
   * Open the editor of the access duration.
   */
  protected editDuration(): void {
    this.durationEdit()?.open();
  }

  #ivasErrorEffect = effect(() => {
    if (this.ivasError()) {
      this.#notificationService.showError('Error fetching verification addresses.');
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
    this.showTransition.set(true);
    setTimeout(() => this.showTransition.set(false), 300);
    const id = this.id();
    if (id) {
      const ar = this.#loadedRequest(id);
      if (ar) {
        this.#cachedRequest.set(ar);
      } else {
        // If not, we need to fetch it now
        this.#accessRequestService.loadAccessRequest(id);
      }
    }
  }

  /**
   * Find the request with the given ID among those the service has already fetched,
   * individually or as part of a list.
   * @param id - the ID of the access request
   * @returns the access request, or undefined if it has not been fetched
   */
  #loadedRequest(id: string): AccessRequest | undefined {
    const ar = this.#request.error() ? undefined : this.#request.value();
    if (ar?.id === id) return ar;
    const requests = this.#requests.error() ? [] : this.#requests.value();
    return requests.find((ar: AccessRequest) => ar.id === id);
  }

  /**
   * Navigate back to the last page (usually the access request manager)
   */
  goBack(): void {
    this.showTransition.set(true);
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
        // take over the copy the service has updated, as this one is a snapshot
        this.#cachedRequest.update((ar) => ar && (this.#loadedRequest(id) ?? ar));
        this.#notificationService.showSuccess(
          `Access request was successfully modified.`,
        );
      },
      error: (err) => {
        console.debug(err);
        // a 422 carries the reason the backend refused the change
        const detail =
          err instanceof HttpErrorResponse && err.status === 422
            ? err.error?.detail
            : undefined;
        this.#notificationService.showError(
          typeof detail === 'string'
            ? `Access request could not be modified: ${detail}`
            : 'Access request could not be modified. Please try again later',
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
    if (this.periodWarning() === 'ended') {
      this.#explainEndedPeriod(request);
      return;
    }
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
      message: html`<p>
          Please confirm that the access request shall be
          <strong>allowed</strong>
          ${startDateInFuture ? html`for the period between <strong>${startDate}</strong> and` : 'until'}
          <strong>${endDate}</strong>, and coupled to the address ${ivaType}:
          ${iva.value}.
        </p>
        <p>
          <strong
            >Once allowed, no further changes can be made to the access request!</strong
          >
        </p>`,
      cancelText: 'Cancel',
      confirmText: 'Confirm allowance',
      confirmClass: 'success',
      callback: (approvalConfirmed) => {
        if (approvalConfirmed) this.#allowAndGoBack();
      },
    });
  }

  /**
   * Explain why a request whose access period has ended cannot be allowed,
   * and offer to open the editor of the access duration.
   * @param request - the access request
   */
  #explainEndedPeriod(request: AccessRequest): void {
    const endDate = this.#datePipe.transform(
      request.access_ends,
      this.friendlyDateFormat,
    );
    this.#confirmationService.confirm({
      title: 'The access period has ended',
      message: html`<p>
          The requested access period ended on <strong>${endDate}</strong>, so the
          access request cannot be allowed as it is.
        </p>
        <p>Set a new end date before allowing the request, or deny it.</p>`,
      cancelText: 'Cancel',
      confirmText: 'Edit access duration',
      callback: (edit) => {
        if (edit) this.editDuration();
      },
    });
  }

  /**
   * Deny the access request after confirmation.
   */
  safeDeny(): void {
    this.#confirmationService.confirm({
      title: 'Confirm denial of the access request',
      message: html`<p>
          Please confirm that the access request shall be <strong>denied</strong>.
        </p>
        <p>
          <strong
            >Once denied, no further changes can be made to the access request!</strong
          >
        </p>`,
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
    // explain an ended period first, as discarding the edits would not help
    if (action === 'allow' && this.periodWarning() === 'ended') {
      this.safeAllow();
    } else if (this.hasPendingEdits()) {
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
