/**
 * User registration component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Component, computed, inject, linkedSignal } from '@angular/core';
import { FormField, form, required } from '@angular/forms/signals';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';

import { AcademicTitle, UserBasicData } from '@app/auth/models/user';
import { AuthService } from '@app/auth/services/auth';
import { Notifier } from '@app/shared/services/notification';

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
})
export class Register {
  #notify = inject(Notifier);
  #authService = inject(AuthService);

  user = this.#authService.user;

  allTitles: AcademicTitle[] = [null, 'Dr.', 'Prof.'];

  /**
   * The form model, with the title of a re-registering user pre-populated
   */
  protected model = linkedSignal<
    AcademicTitle | undefined,
    { title: AcademicTitle; accepted: boolean }
  >({
    source: () => this.user()?.title,
    computation: (title, previous) => ({
      title: title || previous?.value.title || null,
      accepted: previous?.value.accepted ?? false,
    }),
  });

  protected registerForm = form(this.model, (p) => {
    required(p.accepted);
  });

  protected submitDisabled = computed(() => !this.registerForm().valid());

  allowNavigation = false; // used by canDeactivate guard

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
