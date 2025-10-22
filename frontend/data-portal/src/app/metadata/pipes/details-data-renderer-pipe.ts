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
    item: any,
    accessor: string,
    storageLabels?: wellKnownValues,
  ): string {
    let value = item;
    value = accessor
      .split('.')
      .reduce(
        (acc, key) =>
          typeof acc === 'object' ? (acc as Record<string, any>)[key] : undefined,
        value,
      );
    if (value === null || value === undefined) {
      return 'N/A';
    }
    switch (columnDef) {
      case 'phenotype':
        if (Array.isArray(value)) {
          return `${value.join(', ')}`;
        }
        return value;
      case 'size':
        return `${ParseBytes.prototype.transform(value)}`;
      case 'origin':
        return `${Capitalise.prototype.transform(UnderscoreToSpace.prototype.transform(value))}`;
      case 'location':
        return `${storageLabels && storageLabels[value] ? storageLabels[value] : value}`;
      case 'sex':
        return `${Capitalise.prototype.transform((value as string).toLowerCase())}`;
      default:
        return `${value}`;
    }
  }
}
