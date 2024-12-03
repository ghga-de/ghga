import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatNavList } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';

/**
 * This is the site header component
 */
@Component({
  selector: 'app-site-header',
  templateUrl: './site-header.component.html',
  standalone: true,
  imports: [MatToolbarModule, MatNavList, MatButtonModule, MatIconModule, RouterLink],
  styleUrl: './site-header.component.scss',
})
export class SiteHeaderComponent {
  #router = inject(Router);
  #authService = inject(AuthService);
  isLoggedIn = this.#authService.isLoggedIn;

  route: string = '';

  constructor() {
    this.#router.events.subscribe((event) => {
      if (event instanceof NavigationEnd) {
        this.route = this.#router.url;
      } else return;
    });
  }

  /**
   * User login
   */
  onLogin(): void {
    this.#authService.login();
  }

  /**
   * User logout
   */
  onLogout(): void {
    this.#authService.logout();
  }
}
