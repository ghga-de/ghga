import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ShowSessionComponent } from '@app/portal/features/show-session/show-session.component';
import { SiteFooterComponent } from '@app/portal/features/site-footer/site-footer.component';
import { SiteHeaderComponent } from '@app/portal/features/site-header/site-header.component';

/**
 * This is the root component of the application.
 */
@Component({
  selector: 'app-root',
  imports: [
    RouterOutlet,
    SiteHeaderComponent,
    SiteFooterComponent,
    ShowSessionComponent,
  ],
  templateUrl: './app.component.html',
})
export class AppComponent {}
