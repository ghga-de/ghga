import { Component, inject } from '@angular/core';
import { ConfigService } from '@app/shared/services/config.service';

/**
 * This is the home page component
 */
@Component({
  selector: 'app-home-page',
  imports: [],
  templateUrl: './home-page.component.html',
})
export class HomePageComponent {
  #config = inject(ConfigService);

  massUrl = this.#config.massUrl; // just to show that we can access the config service
}
