/**
 * Page component for creating a new upload grant for a given box.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

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
import { toSignal } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import {
  MatDatepickerInputEvent,
  MatDatepickerModule,
} from '@angular/material/datepicker';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';
import { RouterLink } from '@angular/router';
import { DisplayUser, UserService } from '@app/auth/services/user';
import { IvaStatePipe } from '@app/ivas/pipes/iva-state-pipe';
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { IvaService } from '@app/ivas/services/iva';
import { UserExtIdPipe } from '@app/shared/pipes/user-ext-id-pipe';
import { NavigationTrackingService } from '@app/shared/services/navigation';
import { NotificationService } from '@app/shared/services/notification';
import { DATE_INPUT_FORMAT_HINT } from '@app/shared/utils/date-formats';
import { UploadGrantBase, VALID_GRANT_DAYS } from '@app/upload/models/grant';
import { UploadBoxService } from '@app/upload/services/upload-box';

/** Max users to show in the search results list */
const MAX_USER_RESULTS = 10;

/**
 * Formats a Date as an ISO date-only string (YYYY-MM-DD).
 * @param date - the date to format
 * @returns the formatted date string
 */
function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/**
 * Page for creating a new upload grant for a specific upload box.
 * Allows data stewards to search for a user, select an IVA, and set a validity period.
 */
@Component({
  selector: 'app-upload-grant-creation',
  imports: [
    MatButtonModule,
    MatCardModule,
    MatDatepickerModule,
    MatFormFieldModule,
    MatInputModule,
    MatIcon,
    MatProgressSpinner,
    MatRadioModule,
    ReactiveFormsModule,
    RouterLink,
    IvaStatePipe,
    IvaTypePipe,
    UserExtIdPipe,
  ],
  templateUrl: './upload-grant-creation.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UploadGrantCreationComponent implements OnInit {
  #uploadBoxService = inject(UploadBoxService);
  #userService = inject(UserService);
  #ivaService = inject(IvaService);
  #notification = inject(NotificationService);
  #location = inject(NavigationTrackingService);

  /** Route parameter: the ID of the upload box to grant access to. */
  boxId = input.required<string>();

  /** Whether to apply the slide-in view transition animation. */
  showTransition = false;

  /** The upload box being granted access to. */
  box = computed(() =>
    this.#uploadBoxService.uploadBox.error()
      ? undefined
      : this.#uploadBoxService.uploadBox.value(),
  );

  /** Current text in the user search field. */
  searchQuery = signal('');

  /** The user selected from the search results. */
  selectedUser = signal<DisplayUser | null>(null);

  /**
   * The IVA ID selected for the grant.
   * `undefined` means the user has not yet made a choice.
   */
  selectedIvaId = signal<string | undefined>(undefined);

  /** Whether the grant creation request is in flight. */
  isSubmitting = signal(false);

  /** Today at midnight, used as date boundaries. */
  readonly today: Date = (() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  })();

  /** Default valid_until date: today + VALID_GRANT_DAYS. */
  readonly defaultUntilDate: Date = (() => {
    const d = new Date(this.today);
    d.setDate(d.getDate() + VALID_GRANT_DAYS);
    return d;
  })();

  /** Minimum selectable date for valid_from (today). */
  readonly minFromDate = this.today;

  /** Minimum selectable date for valid_until; updated when validFrom changes. */
  minUntilDate: Date = (() => {
    const d = new Date(this.today);
    d.setDate(d.getDate() + 1);
    return d;
  })();

  /** The format hint shown below date inputs. */
  readonly dateInputFormatHint = DATE_INPUT_FORMAT_HINT;

  /** Form control for the valid_from date. */
  readonly fromFormControl = new FormControl<Date | null>(this.today, [
    Validators.required,
  ]);

  /** Form control for the valid_until date. */
  readonly untilFormControl = new FormControl<Date | null>(this.defaultUntilDate, [
    Validators.required,
  ]);

  /** Reactive validity of the from date form control. */
  readonly #fromStatus = toSignal(this.fromFormControl.statusChanges, {
    initialValue: this.fromFormControl.status,
  });

  /** Reactive validity of the until date form control. */
  readonly #untilStatus = toSignal(this.untilFormControl.statusChanges, {
    initialValue: this.untilFormControl.status,
  });

  /**
   * Users matching the current search query, capped at MAX_USER_RESULTS.
   * Filters by displayName, email, and ext_id.
   */
  filteredUsers = computed(() => {
    const query = this.searchQuery().trim().toLowerCase();
    if (!query) return [];
    const users = this.#userService.users.value();
    return users
      .filter(
        (u) =>
          u.displayName.toLowerCase().includes(query) ||
          u.email.toLowerCase().includes(query) ||
          u.ext_id.toLowerCase().includes(query),
      )
      .slice(0, MAX_USER_RESULTS);
  });

  /** Whether the user list is still loading. */
  usersLoading = computed(() => this.#userService.users.isLoading());

  /** The IVAs of the currently selected user. */
  userIvas = computed(() => this.#ivaService.userIvas.value());

  /** Whether the IVA list is still loading. */
  ivasLoading = computed(() => this.#ivaService.userIvas.isLoading());

  /** Whether the IVA resource errored. */
  ivasError = computed(() => !!this.#ivaService.userIvas.error());

  /** Whether the user has made an explicit IVA choice (including "No IVA"). */
  ivaSelectionDone = computed(() => this.selectedIvaId() !== undefined);

  /** Whether the "Create Upload Grant" button should be enabled. */
  canSubmit = computed(
    () =>
      !!this.selectedUser() &&
      this.ivaSelectionDone() &&
      !this.isSubmitting() &&
      this.#fromStatus() === 'VALID' &&
      this.#untilStatus() === 'VALID',
  );

  /** When the selected user changes, reload their IVAs and reset the IVA selection. */
  #userChangedEffect = effect(() => {
    const user = this.selectedUser();
    this.selectedIvaId.set(undefined);
    if (user) {
      this.#ivaService.loadUserIvas(user.id);
    }
  });

  /** @inheritdoc */
  ngOnInit(): void {
    this.showTransition = true;
    setTimeout(() => (this.showTransition = false), 300);

    this.#userService.loadUsers();
    const id = this.boxId();
    if (id) {
      const existing = this.#uploadBoxService.uploadBox.value();
      if (!existing || existing.id !== id) {
        this.#uploadBoxService.loadUploadBox(id);
      }
    }
  }

  /**
   * Navigate back to the upload box detail page with the correct slide-out transition.
   */
  navigateBack(): void {
    this.showTransition = true;
    setTimeout(() => {
      this.#location.back(['/upload-box-manager', this.boxId()]);
    });
  }

  /**
   * Select a user from the search results.
   * @param user - the user to select
   */
  selectUser(user: DisplayUser): void {
    this.selectedUser.set(user);
    this.searchQuery.set('');
  }

  /**
   * Clear the current user selection and go back to search.
   */
  clearUser(): void {
    this.selectedUser.set(null);
    this.selectedIvaId.set(undefined);
  }

  /**
   * Handle from-date changes to keep the minUntilDate constraint in sync.
   * @param event - The datepicker input event
   */
  fromDateChanged(event: MatDatepickerInputEvent<Date>): void {
    if (event.value) {
      const nextDay = new Date(event.value);
      nextDay.setDate(nextDay.getDate() + 1);
      this.minUntilDate = nextDay;
      this.untilFormControl.updateValueAndValidity();
    }
  }

  /**
   * Submit the form to create the upload grant.
   * On success, navigate back to the box detail page.
   */
  submit(): void {
    const user = this.selectedUser();
    if (!user) return;
    this.isSubmitting.set(true);
    const from = this.fromFormControl.value;
    const until = this.untilFormControl.value;
    if (!from || !until) return;
    const payload: UploadGrantBase = {
      user_id: user.id,
      iva_id: this.selectedIvaId() ?? null,
      box_id: this.boxId(),
      valid_from: toIsoDate(from),
      valid_until: toIsoDate(until),
    };
    this.#uploadBoxService
      .createUploadGrant(payload, {
        name: user.displayName,
        email: user.email,
        title: user.title ?? null,
      })
      .subscribe({
        next: () => {
          this.#notification.showSuccess('Upload grant created successfully.');
          this.#location.back(['/upload-box-manager', this.boxId()]);
        },
        error: () => {
          this.#notification.showError(
            'Failed to create upload grant. Please try again.',
          );
          this.isSubmitting.set(false);
        },
      });
  }
}
