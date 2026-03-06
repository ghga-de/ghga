/**
 * Paginator internationalization providers.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Provider } from '@angular/core';
import { MatPaginatorIntl } from '@angular/material/paginator';

/**
 * Creates a paginator provider with a custom page-size selector label.
 * @param itemsPerPageLabel - the label text for the page-size selector
 * @returns provider configuration for MatPaginatorIntl
 */
export function providePaginatorIntl(itemsPerPageLabel: string): Provider {
  return {
    provide: MatPaginatorIntl,
    useFactory: () => {
      const paginatorIntl = new MatPaginatorIntl();
      paginatorIntl.itemsPerPageLabel = itemsPerPageLabel;
      return paginatorIntl;
    },
  };
}
