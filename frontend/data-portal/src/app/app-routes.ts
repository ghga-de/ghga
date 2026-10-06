/**
 * The main app routes
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { inject, Service } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterStateSnapshot, Routes, TitleStrategy } from '@angular/router';
import { canDeactivate as canDeactivateAuth } from './auth/features/can-deactivate';
import { AuthService } from './auth/services/auth';
import { UserService } from './auth/services/user';
import { pendingEditsGuard } from './shared/features/pending-edits';

export const routes: Routes = [
  // public routes
  {
    path: '',
    loadComponent: () =>
      import('./portal/features/home-page/home-page').then((m) => m.HomePage),
    title: 'Home',
  },
  {
    path: 'browse',
    loadComponent: () =>
      import('./metadata/features/metadata-browser/metadata-browser').then(
        (m) => m.MetadataBrowser,
      ),
    title: 'Browse Datasets',
  },
  {
    path: 'metadata-validator',
    loadComponent: () =>
      import('./tools/features/metadata-validator/metadata-validator').then(
        (m) => m.MetadataValidator,
      ),
    title: 'Validate Metadata',
  },
  {
    path: 'schemapack-playground',
    loadComponent: () =>
      import('./tools/features/schemapack-playground/schemapack-playground').then(
        (m) => m.SchemapackPlayground,
      ),
    title: 'Schemapack Playground',
  },
  {
    path: 'dataset/:id',
    loadComponent: () =>
      import('./metadata/features/dataset-details/dataset-details').then(
        (m) => m.DatasetDetailsPage,
      ),
    title: 'Dataset Details',
  },
  {
    path: 's/:id',
    loadComponent: () =>
      import('./metadata/features/study-details/study-details').then(
        (m) => m.StudyDetails,
      ),
    title: 'Study Details',
  },
  {
    path: 'study/:id',
    loadComponent: () =>
      import('./metadata/features/study-details/study-details').then(
        (m) => m.StudyDetails,
      ),
    title: 'Study Details',
  },
  // routes that need user authentication
  {
    path: 'account',
    canActivate: [() => inject(AuthService).guardAuthenticated()],
    loadComponent: () =>
      import('./auth/features/account/account').then((m) => m.Account),
    title: 'User Account',
  },
  // routes that are only available to data stewards
  {
    path: 'iva-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    loadComponent: () =>
      import('./ivas/features/iva-manager/iva-manager').then((m) => m.IvaManager),
    title: 'IVA Manager',
  },
  {
    path: 'access-request-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./access-requests/features/access-request-manager/access-request-manager').then(
            (m) => m.AccessRequestManager,
          ),
        title: 'Access Request Manager',
      },
      {
        path: ':id',
        canDeactivate: [pendingEditsGuard],
        loadComponent: () =>
          import('./access-requests/features/access-request-manager-detail/access-request-manager-detail').then(
            (m) => m.AccessRequestManagerDetail,
          ),
        title: 'Access Request Details',
        data: { transition: 'detail' },
      },
    ],
  },
  {
    path: 'user-manager',
    providers: [UserService],
    canActivate: [() => inject(AuthService).guardDataSteward()],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./auth/features/user-manager/user-manager').then(
            (m) => m.UserManager,
          ),
        title: 'User Manager',
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./auth/features/user-manager-detail/user-manager-detail').then(
            (m) => m.UserManagerDetail,
          ),
        title: 'User Details',
        data: { transition: 'detail' },
      },
    ],
  },
  {
    path: 'access-grant-manager',
    canActivate: [() => inject(AuthService).guardDataSteward()],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./access-requests/features/access-grant-manager/access-grant-manager').then(
            (m) => m.AccessGrantManager,
          ),
        title: 'Access Grant Manager',
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./access-requests/features/access-grant-manager-details/access-grant-manager-details').then(
            (m) => m.AccessGrantManagerDetails,
          ),
        title: 'Access Grant Manager Details',
      },
    ],
  },
  {
    path: 'upload-box-manager',
    providers: [UserService],
    canActivate: [() => inject(AuthService).guardDataSteward()],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./upload/features/upload-box-manager/upload-box-manager').then(
            (m) => m.UploadBoxManager,
          ),
        title: 'Upload Box Manager',
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./upload/features/upload-box-manager-detail/upload-box-manager-detail').then(
            (m) => m.UploadBoxManagerDetail,
          ),
        title: 'Upload Box Details',
        data: { transition: 'detail' },
      },
      {
        path: ':boxId/grant/new',
        loadComponent: () =>
          import('./upload/features/upload-grant-creation/upload-grant-creation').then(
            (m) => m.UploadGrantCreation,
          ),
        title: 'New Upload Grant',
      },
      {
        path: ':boxId/grant/:grantId',
        loadComponent: () =>
          import('./upload/features/upload-grant-manager-details/upload-grant-manager-details').then(
            (m) => m.UploadGrantManagerDetails,
          ),
        title: 'Upload Grant Details',
      },
    ],
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
      import('./auth/features/register/register').then((m) => m.Register),
    title: 'Registration',
  },
  {
    path: 'setup-totp',
    canActivate: [() => inject(AuthService).guardSetupTotp()],
    canDeactivate: [canDeactivateAuth],
    loadComponent: () =>
      import('./auth/features/setup-totp/setup-totp').then((m) => m.SetupTotp),
    title: 'Set up TOTP',
  },
  {
    path: 'confirm-totp',
    canActivate: [() => inject(AuthService).guardConfirmTotp()],
    canDeactivate: [canDeactivateAuth],
    loadComponent: () =>
      import('./auth/features/confirm-totp/confirm-totp').then((m) => m.ConfirmTotp),
    title: 'Confirm TOTP',
  },
  // fallback route
  {
    path: '**',
    loadComponent: () =>
      import('./portal/features/page-not-found/page-not-found').then(
        (m) => m.PageNotFound,
      ),
    title: 'Page not found',
  },
];

/**
 * This strategy provides a simpler way to set the page title.
 * The routes (above) still set a title but it uses a template syntax
 * to extend the title by the GHGA Data Portal string.
 */
@Service()
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
