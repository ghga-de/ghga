import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SiteFooterComponent } from '@app/portal/features/site-footer/site-footer.component';
import { SiteHeaderComponent } from '@app/portal/features/site-header/site-header.component';
import { ConfigService } from '@app/shared/services/config.service';

/**
 * This is the root component of the application.
 */
@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SiteHeaderComponent, SiteFooterComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {
  title = 'data-portal';

  #config = inject(ConfigService);

  massUrl = this.#config.massUrl; // just to show that we can access the config service
}
