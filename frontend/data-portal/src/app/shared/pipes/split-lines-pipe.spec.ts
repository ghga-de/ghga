/**
 * These are the unit tests for the NewlineSplit pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { SplitLinesPipe } from './split-lines-pipe';

describe('NewlineSplit', () => {
  it('can create an instance', () => {
    const pipe = new SplitLinesPipe();
    expect(pipe).toBeTruthy();
  });

  it('should return an empty array if input is an empty string', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('');
    expect(result).toStrictEqual([]);
  });

  it('should return an array with the original (trimmed) string if no newline is present', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('\thello world ');
    expect(result).toStrictEqual(['hello world']);
  });

  it('should return an array of strings split by newline characters', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('hello\nworld');
    expect(result).toStrictEqual(['hello', 'world']);
  });

  it('should return an array of strings split by \\n sequence', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('hello\\nworld');
    expect(result).toStrictEqual(['hello', 'world']);
  });

  it('should split all instances of newlines in a text', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('hello\nworld\\r\\nhow\r\nare\r\\nyou?');
    expect(result).toStrictEqual(['hello', 'world', 'how', 'are', 'you?']);
  });

  it('should discard duplicate newlines, and carriage return sequences', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('hello\r\n\\r\\n\n\rworld');
    expect(result).toStrictEqual(['hello', 'world']);
  });

  it('should return an array with the split string with tabs in the middle of lines intact but remove those at the beginning or end of lines', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('hello \tworld\n\thow are you?');
    expect(result).toStrictEqual(['hello \tworld', 'how are you?']);
  });

  it('should not remove backslashes at the start or end of lines', () => {
    const pipe = new SplitLinesPipe();
    const result = pipe.transform('\\hello world\\');
    expect(result).toStrictEqual(['\\hello world\\']);
  });
});
