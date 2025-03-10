/**
 * Date formats used throughout the application.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { MatDateFormats } from '@angular/material/core';
import { enGB } from 'date-fns/locale';

export const DEFAULT_DATE_LOCALE = enGB;

export const DEFAULT_DATE_OUTPUT_FORMAT = 'yyyy-MM-dd';
export const DEFAULT_DATE_INPUT_FORMAT = 'yyyy-MM-dd';
export const FRIENDLY_DATE_FORMAT = 'd MMMM y';
export const DATE_INPUT_FORMAT_HINT = 'YYYY-MM-DD';

export const DEFAULT_DATE_FORMATS: MatDateFormats = {
  parse: {
    dateInput: [
      'yyyy-MM-dd',
      'dd.MM.yyyy',
      'dd/MM/yyyy',
      'd.M.yyyy',
      'd/M/yyyy',
      'dd.M.yyyy',
      'dd/M/yyyy',
      'd.MM.yyyy',
      'd/MM/yyyy',
    ],
  },
  display: {
    dateInput: DEFAULT_DATE_INPUT_FORMAT,
    monthYearLabel: 'MMM yyyy',
    dateA11yLabel: 'LL',
    monthYearA11yLabel: 'MMMM yyyy',
  },
};
