import { Component, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatNavList } from '@angular/material/list';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink } from '@angular/router';
import { AuthService } from '@app/auth/services/auth.service';

/**
 * This is the site header component
 */
@Component({
  selector: 'app-site-header',
  templateUrl: './site-header.component.html',
  standalone: true,
  imports: [MatToolbarModule, MatNavList, MatButtonModule, RouterLink],
})
export class SiteHeaderComponent {
  #authService = inject(AuthService);

  isLoggedIn = this.#authService.isLoggedIn;

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
