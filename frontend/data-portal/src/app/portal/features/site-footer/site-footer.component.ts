import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * This is the site footer component
 */
@Component({
  selector: 'app-site-footer',
  imports: [RouterLink],
  templateUrl: './site-footer.component.html',
  styleUrl: './site-footer.component.scss',
})
export class SiteFooterComponent {
  year = new Date().getFullYear();
}
