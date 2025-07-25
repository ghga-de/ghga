/**
 * The main app routes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Injectable } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, Routes, TitleStrategy } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';
import { canDeactivate as canDeactivateAuth } from './auth/features/can-deactivate.guard';

export const routes: Routes = [
  // public routes
  {
    path: '',
    loadComponent: () =>
      import('./portal/features/home-page/home-page.component').then(
        (m) => m.HomePageComponent,
      ),
    title: 'Home',
  },
  {
    path: 'browse',
    loadComponent: () =>
      import('./metadata/features/metadata-browser/metadata-browser.component').then(
        (m) => m.MetadataBrowserComponent,
      ),
    title: 'Browse Datasets',
  },
  {
    path: 'metadata-validator',
    loadComponent: () =>
      import('./tools/features/metadata-validator/metadata-validator.component').then(
        (m) => m.MetadataValidatorComponent,
      ),
    title: 'Validate Metadata',
  },
  {
    path: 'schemapack-playground',
    loadComponent: () =>
      import(
        './tools/features/schemapack-playground/schemapack-playground.component'
      ).then((m) => m.SchemapackPlaygroundComponent),
    title: 'Schemapack Playground',
  },
  {
    path: 'dataset/:id',
    loadComponent: () =>
      import('./metadata/features/dataset-details/dataset-details.component').then(
        (m) => m.DatasetDetailsComponent,
      ),
    title: 'Dataset Details',
  },
  // routes that need user authentication
  {
    path: 'work-package',
    canActivate: [() => inject(AuthService).guardAuthenticated()],
    loadComponent: () =>
      import('./work-packages/features/work-package/work-package.component').then(
        (m) => m.WorkPackageComponent,
      ),
    title: 'Download or Upload Datasets',
  },
  {
    path: 'account',
    canActivate: [() => inject(AuthService).guardAuthenticated()],
    loadComponent: () =>
      import('./portal/features/account/account.component').then(
        (m) => m.AccountComponent,
      ),
    title: 'User Account',
  },
  // routes that are only available to data stewards
  {
    path: 'iva-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    loadComponent: () =>
      import(
        './verification-addresses/features/iva-manager/iva-manager.component'
      ).then((m) => m.IvaManagerComponent),
    title: 'IVA Manager',
  },
  {
    path: 'access-request-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    loadComponent: () =>
      import(
        './access-requests/features/access-request-manager/access-request-manager.component'
      ).then((m) => m.AccessRequestManagerComponent),
    title: 'Access Request Manager',
  },
  {
    path: 'user-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    loadComponent: () =>
      import('./auth/features/user-manager/user-manager.component').then(
        (m) => m.UserManagerComponent,
      ),
    title: 'User Manager',
  },
  {
    path: 'user-manager/:id',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    loadComponent: () =>
      import('./auth/features/user-manager-detail/user-manager-detail.component').then(
        (m) => m.UserManagerDetailComponent,
      ),
    title: 'User Details',
  },
  // routes used in the authentication flows
  {
    path: 'oauth/callback',
    canActivate: [() => inject(AuthService).guardCallback()],
    children: [],
  },
  {
    path: 'register',
    canActivate: [() => inject(AuthService).guardRegister()],
    canDeactivate: [canDeactivateAuth],
    loadComponent: () =>
      import('./auth/features/register/register.component').then(
        (m) => m.RegisterComponent,
      ),
    title: 'Registration',
  },
  {
    path: 'setup-totp',
    canActivate: [() => inject(AuthService).guardSetupTotp()],
    canDeactivate: [canDeactivateAuth],
    loadComponent: () =>
      import('./auth/features/setup-totp/setup-totp.component').then(
        (m) => m.SetupTotpComponent,
      ),
    title: 'Set up TOTP',
  },
  {
    path: 'confirm-totp',
    canActivate: [() => inject(AuthService).guardConfirmTotp()],
    canDeactivate: [canDeactivateAuth],
    loadComponent: () =>
      import('./auth/features/confirm-totp/confirm-totp.component').then(
        (m) => m.ConfirmTotpComponent,
      ),
    title: 'Confirm TOTP',
  },
  // fallback route
  {
    path: '**',
    loadComponent: () =>
      import('../app/portal/features/page-not-found/page-not-found.component').then(
        (m) => m.PageNotFoundComponent,
      ),
    title: 'Page not found',
  },
];

/**
 * This strategy provides a simpler way to set the page title.
 * The routes (above) still set a title but it uses a template syntax
 * to extend the title by the GHGA Data Portal string.
 */
@Injectable({ providedIn: 'root' })
export class TemplatePageTitleStrategy extends TitleStrategy {
  TITLE_TEMPLATE = '#title | GHGA Data Portal';

  #title = inject(Title);

  /**
   * This gets called whenever the router requests a new title for a site.
   * @param routerState passes the current route to the function.
   */
  override updateTitle(routerState: RouterStateSnapshot) {
    const title = this.buildTitle(routerState);
    if (title !== undefined) {
      this.#title.setTitle(this.TITLE_TEMPLATE.replace('#title', title));
    }
  }
}
