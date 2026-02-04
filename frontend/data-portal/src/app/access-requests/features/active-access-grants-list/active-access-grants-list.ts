/**
 * Show access requests that have been granted.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe } from '@angular/common';
import { Component, computed, inject, OnInit } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterModule } from '@angular/router';
import { AccessRequestService } from '@app/access-requests/services/access-request';
import { AuthService } from '@app/auth/services/auth';
import { IvaTypePipe } from '@app/ivas/pipes/iva-type-pipe';
import { IvaService } from '@app/ivas/services/iva';
import { FRIENDLY_DATE_FORMAT } from '@app/shared/utils/date-formats';
import { StencilComponent } from '../../../shared/ui/stencil/stencil/stencil';

/**
 * This component shows a list of access grants that have been granted.
 */
@Component({
  selector: 'app-granted-access-grants-list',
  imports: [
    RouterLink,
    StencilComponent,
    DatePipe,
    MatIconModule,
    MatButtonModule,
    RouterModule,
    IvaTypePipe,
  ],
  templateUrl: './active-access-grants-list.html',
})
export class ActiveAccessGrantsListComponent implements OnInit {
  readonly friendlyDateFormat = FRIENDLY_DATE_FORMAT;
  #ars = inject(AccessRequestService);
  #iva = inject(IvaService);
  #auth = inject(AuthService);

  protected activeGrants = computed(() => this.#ars.activeUserAccessGrants());
  protected isLoading = this.#ars.userAccessGrants.isLoading;
  protected hasError = this.#ars.userAccessGrants.error;

  #userId = computed<string | undefined>(() => this.#auth.user()?.id || undefined);

  #userIvas = computed(() =>
    this.#iva.userIvas.error() ? [] : this.#iva.userIvas.value(),
  );

  protected grantWithIvas = computed(() =>
    this.activeGrants().map((g) => {
      return { ...g, iva: this.#userIvas().find((iva) => iva.id === g.iva_id) };
    }),
  );

  protected anyActiveGrantWithValidIva = computed(() =>
    Object.values(this.grantWithIvas()).some((x) => x.iva?.state === 'Verified'),
  );

  /**
   * On initialisation, load the current user's ID to obtain their IVAs
   */
  ngOnInit() {
    this.#iva.loadUserIvas(this.#userId());
  }
}
