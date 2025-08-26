/**
 * Component for displaying detailed information about a specific user.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, OnInit, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { AccessGrantStatusClassPipe } from '@app/access-requests/pipes/access-grant-status-class.pipe';
import { AccessRequestStatusClassPipe } from '@app/access-requests/pipes/access-request-status-class.pipe';
import { AccessRequestService } from '@app/access-requests/services/access-request.service';
import { UserStatus } from '@app/auth/models/user';
import { DisplayUser, UserService } from '@app/auth/services/user.service';
import { DatePipe } from '@app/shared/pipes/date.pipe';
import { ConfirmationService } from '@app/shared/services/confirmation.service';
import { NavigationTrackingService } from '@app/shared/services/navigation.service';
import { NotificationService } from '@app/shared/services/notification.service';
import {
  DEFAULT_TIME_ZONE,
  FRIENDLY_DATE_FORMAT,
} from '@app/shared/utils/date-formats';
import { IvaStatePipe } from '@app/verification-addresses/pipes/iva-state.pipe';
import { IvaTypePipe } from '@app/verification-addresses/pipes/iva-type.pipe';
import { IvaService } from '@app/verification-addresses/services/iva.service';
import { DeletionConfirmationDialogComponent } from '../deletion-confirmation-dialog/deletion-confirmation-dialog.component';

/**
 * User Manager Detail component.
 *
 * This component displays detailed information about a specific user
 * and allows data stewards to view and manage individual user data.
 */
@Component({
  selector: 'app-user-manager-detail',
  imports: [
    MatButtonModule,
    MatChipsModule,
    MatIconModule,
    MatCardModule,
    MatButtonModule,
    MatTooltipModule,
    DatePipe,
    RouterLink,
    IvaStatePipe,
    IvaTypePipe,
    AccessGrantStatusClassPipe,
    AccessRequestStatusClassPipe,
  ],
  providers: [UserService, CommonDatePipe],
  templateUrl: './user-manager-detail.component.html',
  styleUrl: './user-manager-detail.component.scss',
})
export class UserManagerDetailComponent implements OnInit {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  readonly periodTimeZone = DEFAULT_TIME_ZONE;

  showTransition = false;

  #userService = inject(UserService);

  #location = inject(NavigationTrackingService);
  #dialog = inject(MatDialog);

  id = input.required<string>();
  #user = this.#userService.user;
  #users = this.#userService.users;

  #cachedUser = signal<DisplayUser | undefined>(undefined);

  user = computed<DisplayUser | undefined>(
    () => this.#cachedUser() || (this.#user.error() ? undefined : this.#user.value()),
  );

  loading = computed<boolean>(() => !this.#cachedUser() && this.#user.isLoading());

  error = computed<undefined | 'not found' | 'other'>(() => {
    if (this.#cachedUser()) return undefined;
    const error = this.#user.error();
    if (!error) return undefined;

    return (error as HttpErrorResponse)?.status === 404 ? 'not found' : 'other';
  });

  #confirmationService = inject(ConfirmationService);
  #notificationService = inject(NotificationService);

  #ivaService = inject(IvaService);
  userIvas = computed(() =>
    this.#ivaService.userIvas.error() ? [] : this.#ivaService.userIvas.value(),
  );

  #accessRequestService = inject(AccessRequestService);

  userRequests = computed(() => {
    const id = this.id();
    const requests = this.#accessRequestService.allAccessRequests;
    if (requests.error()) return [];
    return requests.value().filter((r) => r.user_id === id);
  });

  userGrants = computed(() => {
    const id = this.id();
    return this.#accessRequestService.allAccessGrants().filter((g) => g.user_id === id);
  });

  /**
   * On initialization, allow the transition effect,
   * but then remove it so it applies only when we navigate back.
   */
  ngOnInit() {
    this.showTransition = true;
    setTimeout(() => (this.showTransition = false), 300);
    const id = this.id();
    if (id) {
      // Has it been fetched individually already?
      let user = this.#user.error() ? undefined : this.#user.value();
      if (user && user.id === id) {
        this.#cachedUser.set(user);
      } else {
        // Has it been fetched as part of a list?
        const users = this.#users.error() ? [] : this.#users.value();
        user = users.find((user: DisplayUser) => user.id === id);
        if (user) {
          this.#cachedUser.set(user);
        } else {
          // If not, we need to fetch it now
          this.#userService.loadUser(id);
        }
      }
    }
    if (this.id()) {
      this.#ivaService.loadUserIvas(this.id());
      // Note: The following two calls are inefficient.
      // We need to add a way to load only a given user's access requests and grants.
      // This can be also useful for the access grants detail view.
      this.#accessRequestService.loadAllAccessGrants();
      this.#accessRequestService.loadAllAccessRequests();
    }
  }

  /**
   * Navigate back to the last page (usually the user manager)
   */
  goBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/user-manager']);
    });
  }

  /**
   * Delete the user.
   */
  #delete(): void {
    const id = this.user()?.id;
    if (!id) return;
    this.#userService.deleteUser(id).subscribe({
      next: () => {
        this.#notificationService.showSuccess(`User account was successfully deleted.`);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'User account could not be deleted. Please try again later',
        );
      },
    });
  }

  /**
   * Update the user data.
   * @param changes - The changes to apply
   */
  #update(changes: Partial<DisplayUser>): void {
    const id = this.user()?.id;
    if (!id) return;
    this.#userService.updateUser(id, changes).subscribe({
      next: () => {
        this.#notificationService.showSuccess(`User data was successfully modified.`);
      },
      error: (err) => {
        console.debug(err);
        this.#notificationService.showError(
          'User data could not be modified. Please try again later',
        );
      },
    });
  }

  /**
   * Activate and deactivate the user after confirmation.
   * @param isDeactivated Whether the user is currently deactivated (thus we want to reactivate the account)
   */
  safeStatusChange(isDeactivated: Boolean = false): void {
    this.#confirmationService.confirm({
      title: 'Confirm user account deactivation',
      message: `<p>Please confirm that the user account of ${this.user()!.displayName} shall be <strong>${!isDeactivated ? 'de' : ''}activated</strong>.`,
      cancelText: 'Cancel',
      confirmText: `Confirm ${!isDeactivated ? 'de' : ''}activation`,
      confirmClass: 'danger',
      callback: (statusChangeConfirmed) => {
        if (statusChangeConfirmed)
          this.#update({
            status: isDeactivated ? UserStatus.active : UserStatus.inactive,
          });
      },
    });
  }

  /**
   * Delete the user after confirmation.
   */
  safeDeletion(): void {
    const dialogRef = this.#dialog.open(DeletionConfirmationDialogComponent, {
      data: { user: this.user()! },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) this.#delete();
    });
  }
}
