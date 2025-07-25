/**
 * Types for the Pyodide service and its dependents.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

export interface PyodideOutput {
  json_output: string | null;
  error_message: string | null;
  success: boolean;
  output?: string;
}

export interface LogEntry {
  message: string;
  type: 'info' | 'success' | 'error' | 'debug';
  time: string;
}
