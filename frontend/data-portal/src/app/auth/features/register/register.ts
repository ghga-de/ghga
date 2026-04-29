/**
 * User registration component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { FormField, form, required } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';

import { AcademicTitle, UserBasicData } from '@app/auth/models/user';
import { AuthService } from '@app/auth/services/auth';
import { NotificationService } from '@app/shared/services/notification';

/**
 * User registration page
 */
@Component({
  selector: 'app-register',
  imports: [
    FormField,
    MatButtonModule,
    MatCheckboxModule,
    MatFormFieldModule,
    MatSelectModule,
    RouterLink,
  ],
  templateUrl: './register.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RegisterComponent {
  #notify = inject(NotificationService);
  #authService = inject(AuthService);

  user = this.#authService.user;

  allTitles: AcademicTitle[] = [null, 'Dr.', 'Prof.'];

  protected model = signal({ title: null as AcademicTitle, accepted: false });

  protected registerForm = form(this.model, (p) => {
    required(p.accepted);
  });

  protected submitDisabled = computed(() => !this.registerForm().valid());

  allowNavigation = false; // used by canDeactivate guard

  constructor() {
    // if a re-registering user already has a title, pre-populate it
    effect(() => {
      const title = this.user()?.title;
      if (title) {
        this.model.update((m) => ({ ...m, title }));
      }
    });
  }

  /**
   * Cancel registration and log out
   */
  async cancel(): Promise<void> {
    await this.#authService.logout();
  }

  /**
   * Submit registration form
   */
  async register(): Promise<void> {
    if (!this.model().accepted) return;
    const user = this.user();
    if (!user) return;
    const title = this.model().title || null;
    const { id, ext_id, name, email } = user;
    const data: UserBasicData = { name, email, title };
    this.allowNavigation = true;
    const ok = await this.#authService.register(id || null, ext_id, data);
    if (ok) {
      this.#notify.showSuccess('Registration was successful.');
    } else {
      this.allowNavigation = false;
      this.#notify.showError('Registration failed.');
    }
  }
}
