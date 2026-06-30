/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { FormatSchemapackErrorPipe } from './schemapack-error-pipe';

describe('FormatSchemapackErrorPipe', () => {
  let pipe: FormatSchemapackErrorPipe;

  beforeEach(() => {
    pipe = new FormatSchemapackErrorPipe();
  });

  it('should be created', () => {
    expect(pipe).toBeTruthy();
  });

  it('should return an empty string for null input', () => {
    expect(pipe.transform(null)).toBe('');
  });

  it('should return an empty string for an empty string input', () => {
    expect(pipe.transform('')).toBe('');
  });

  it('should remove all box-drawing characters and trim lines', () => {
    const input = `
      ╭──────────────────╮
      │ Error: Something went wrong │
      ╰──────────────────╯
    `;
    const expected = 'Error: Something went wrong';
    expect(pipe.transform(input)).toBe(expected);
  });

  it('should replace vertical bars with two spaces and remove other box-drawing characters', () => {
    const input = `
      ╭──────────────╮
      │ Path: /data/field           │
      │ Message: Invalid value │
      ╰──────────────╯
    `;
    const expected = `Path: /data/field
  Message: Invalid value`;
    expect(pipe.transform(input)).toBe(expected);
  });

  it('should handle multiple lines, leading/trailing spaces, and empty lines correctly', () => {
    const input = `
      ╭────────────────╮
      │ Error in schema validation │
      │                                            │
      │   Path: /items[0]/name       │
      │   Message: Expected string│
      │                                            │
      ╰────────────────╯
    `;
    const expected = `Error in schema validation
  Path: /items[0]/name
  Message: Expected string`;
    expect(pipe.transform(input)).toBe(expected);
  });

  it('should not modify a string without box-drawing characters', () => {
    const input = 'This is a regular error message.';
    expect(pipe.transform(input)).toBe(input);
  });

  it('should handle a complex real-world like error message (single box)', () => {
    const input = `
      ╭──────────────────╮
      │ Error: Validation failed            │
      │ Path: /user/age                       │
      │ Message: Must be a number  │
      │ Path: /user/email                    │
      │ Message: Invalid format         │
      ╰──────────────────╯
    `;
    const expected = `Error: Validation failed
  Path: /user/age
  Message: Must be a number
  Path: /user/email
  Message: Invalid format`;
    expect(pipe.transform(input)).toBe(expected);
  });

  it('should remove only the specified box-drawing characters and preserve others', () => {
    const input = `
      Some text with ╭ and ─ and │ and ╰ and ╮ and ╯.
      Other symbols like @#$%^&*() should remain.
    `;
    const expected = `Some text with  and  and    and  and  and\n.
  Other symbols like @#$%^&*() should remain.`;
    expect(pipe.transform(input)).toBe(expected);
  });

  it('should handle strings with only box-drawing characters', () => {
    const input = '╭─╮│╰╯';
    expect(pipe.transform(input)).toBe('');
  });
});
