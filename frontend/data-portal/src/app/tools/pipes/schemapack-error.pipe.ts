/**
 * A pipe to transform Schemapack errors into more readable messages
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Pipe, PipeTransform } from '@angular/core';

/**
 * A pipe to transform Schemapack errors into more readable messages
 */
@Pipe({
  name: 'formatSchemapackError',
  standalone: true,
})
export class FormatSchemapackErrorPipe implements PipeTransform {
  /**
   * Transforms a raw error string by cleaning up box-drawing characters and whitespace.
   * @param errorString The raw string to format.
   * @returns A formatted, more readable error string.
   */
  static transform(errorString: string | null): string {
    if (!errorString) {
      return '';
    }

    let formattedError = errorString.replace(/[╭─╮│╰╯]/g, (match) => {
      switch (match) {
        case '╭':
        case '╮':
        case '╰':
        case '─':
          return '';
        case '╯':
          return '\n';
        case '│':
          return '  ';
        default:
          return match;
      }
    });
    console.log(formattedError);
    formattedError = formattedError
      .split('\n')
      .filter((line) => line.trim() !== '')
      .map((line) => line.trimEnd())
      .map((line) => line.replace(/^ {2,}/, '  '))
      .map((line) => {
        if (
          line.indexOf('errors.pydantic.dev') !== -1 ||
          line.indexOf('for DataPack') !== -1
        ) {
          return line + '\n';
        } else if (line.indexOf('The provided datapack is not valid') !== -1) {
          return '\n' + line;
        } else {
          return line;
        }
      })
      .join('\n');

    return formattedError.trim();
  }

  /**
   * Transforms the input value using the static transform method.
   * @param value The raw error string to format.
   * @returns A formatted, more readable error string.
   */
  transform(value: string | null): string {
    return FormatSchemapackErrorPipe.transform(value);
  }
}
