/**
 * This pipe takes the column name of a dataset details table and returns a properly formatted element for display
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';
import { Capitalise } from '@app/shared/pipes/capitalise-pipe';
import { ParseBytes } from '@app/shared/pipes/parse-bytes-pipe';
import { UnderscoreToSpace } from '@app/shared/pipes/underscore-to-space-pipe';
import { wellKnownValues } from '../models/well-known-values';

/**
 * Pipe to render dataset details table cell data
 */
@Pipe({
  name: 'detailsDataRenderer',
})
export class DetailsDataRendererPipe implements PipeTransform {
  /**
   * Pipe to render dataset details table cell data
   * @param columnDef Column definition
   * @param item Item data
   * @param accessor Accessor string
   * @param storageLabels Storage label aliases
   * @returns formatted string for display
   */
  transform(
    columnDef: string,
    item: unknown,
    accessor: string,
    storageLabels?: wellKnownValues,
  ): string {
    const value = accessor
      .split('.')
      .reduce<unknown>(
        (acc, key) =>
          acc !== null && typeof acc === 'object'
            ? (acc as Record<string, unknown>)[key]
            : undefined,
        item,
      );
    if (value === null || value === undefined) {
      return 'N/A';
    }
    switch (columnDef) {
      case 'phenotype':
        if (Array.isArray(value)) {
          return `${value.join(', ')}`;
        }
        return `${value}`;
      case 'size':
        return `${ParseBytes.prototype.transform(value as number)}`;
      case 'origin':
        return `${Capitalise.prototype.transform(UnderscoreToSpace.prototype.transform(value as string))}`;
      case 'location': {
        const key = value as string;
        return `${storageLabels && storageLabels[key] ? storageLabels[key] : value}`;
      }
      case 'sex':
        return `${Capitalise.prototype.transform((value as string).toLowerCase())}`;
      default:
        return `${value}`;
    }
  }
}
