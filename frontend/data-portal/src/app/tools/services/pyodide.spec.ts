/**
 * Test the messages of the Pyodide loader.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { installFailureMessage } from './pyodide';

describe('installFailureMessage', () => {
  it('should point at a blocked download for a network error', () => {
    const message = installFailureMessage(
      'schemapack',
      'pyodide.http.AbortError: NetworkError when attempting to fetch resource.',
    );
    expect(message).toContain('Could not download the Python package schemapack.');
    expect(message).toContain('NoScript');
    expect(message).toContain('files.pythonhosted.org');
  });

  it('should treat the Chrome wording of a failed fetch the same way', () => {
    expect(installFailureMessage('schemapack', 'TypeError: Failed to fetch')).toContain(
      'Could not download the Python package schemapack.',
    );
  });

  it('should pass any other error through', () => {
    expect(installFailureMessage('schemapack', 'No matching distribution')).toBe(
      'Failed to install the Python package schemapack: No matching distribution',
    );
  });
});
