/* eslint-disable jsdoc/require-jsdoc */
import { inject } from '@angular/core';
import { Routes } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./portal/features/home-page/home-page.component').then(
        (m) => m.HomePageComponent,
      ),
  },
  {
    path: 'browse',
    loadComponent: () =>
      import('./metadata/features/metadata-browser/metadata-browser.component').then(
        (m) => m.MetadataBrowserComponent,
      ),
  },
  // routes used in the authentication flows
  {
    path: 'oauth/callback',
    canActivate: [() => inject(AuthService).oidcRedirect()],
    children: [],
  },
  // TODO: add guards to the following routes that check the expected state
  // TODO: also add deactivation guards to these routes
  {
    path: 'register',
    loadComponent: () =>
      import('./auth/features/register/register.component').then(
        (m) => m.RegisterComponent,
      ),
  },
  {
    path: 'setup-totp',
    loadComponent: () =>
      import('./auth/features/setup-totp/setup-totp.component').then(
        (m) => m.SetupTotpComponent,
      ),
  },
  {
    path: 'confirm-totp',
    loadComponent: () =>
      import('./auth/features/confirm-totp/confirm-totp.component').then(
        (m) => m.ConfirmTotpComponent,
      ),
  },
];
