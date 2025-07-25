/**
 * This service provides basic pyodide functionality.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal, WritableSignal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { LogEntry, PyodideOutput } from '../models/pyodide';

const PYODIDE_CDN_URL = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/';

/**
 * This service handles the initialization of Pyodide,
 * loading necessary packages, and serves as a basis for running our Python scripts in their own services (like TranspilerService and ValidatorService).
 */
@Injectable({
  providedIn: 'root',
})
export class PyodideService {
  #pyodide: any = null;
  #pyodideLoading: WritableSignal<boolean> = signal(false);
  #pyodideInitialized: WritableSignal<boolean> = signal(false);
  #processLog: WritableSignal<LogEntry[]> = signal([]);
  #micropip: any = null;
  #http = inject(HttpClient);

  readonly isPyodideInitialized = this.#pyodideInitialized.asReadonly();
  readonly getProcessLog = this.#processLog.asReadonly();
  readonly isPyodideLoading = this.#pyodideLoading.asReadonly();

  constructor() {
    this.#initPyodide();
  }

  /**
   * Logs a message to the process log.
   * @param message - the log message
   * @param type - the log type (info, success, error, debug)
   */
  public log(
    message: string,
    type: 'info' | 'success' | 'error' | 'debug' = 'info',
  ): void {
    const time = new Date().toLocaleTimeString();
    this.#processLog.update((currentLog) => [...currentLog, { message, type, time }]);
    if (type === 'success') {
      console.log(message);
    } else {
      console[type](message);
    }
  }

  /**
   *  This function installs a specified package using micropip for the Pyodide environment.
   * @param packageName name of the package to install
   * @returns A promise that resolves when the package is installed successfully.
   */
  async installPackage(packageName: string): Promise<void> {
    if (!this.#pyodideInitialized() || !this.#micropip) {
      this.log('Pyodide not initialized or micropip not loaded.', 'error');
      console.error('Pyodide not initialized or micropip not loaded.');
      return Promise.reject(
        new Error('Pyodide not initialized or micropip not loaded.'),
      );
    }
    return this.#micropip
      .install(packageName, { keep_going: true })
      .then(() => {
        this.log(`Package ${packageName} installed successfully.`, 'success');
      })
      .catch((error: any) => {
        this.log(`Failed to install package ${packageName}: ${error.message}`, 'error');
      });
  }

  /**
   * This function initializes the Pyodide runtime,
   * loads the necessary packages, and prepares the environment for validation.
   * It also loads a custom YAML schema from the assets folder into the Pyodide filesystem.
   * It should be called once at the start of the application.
   * If Pyodide is already loading or initialized, it will return early.
   * @returns A promise that resolves when Pyodide is fully initialized.
   * @throws Will throw an error if Pyodide fails to initialize or if critical packages fail to load.
   */
  async #initPyodide(): Promise<void> {
    if (this.#pyodideLoading() || this.#pyodideInitialized()) {
      return;
    }

    this.#pyodideLoading.set(true);
    this.log('Loading Pyodide runtime...', 'info');

    try {
      // Load Pyodide from CDN
      const pyodideScript = document.createElement('script');
      pyodideScript.src = PYODIDE_CDN_URL + 'pyodide.js';
      document.head.appendChild(pyodideScript);

      // Wait for script to load
      await new Promise((resolve, reject) => {
        pyodideScript.onload = resolve;
        pyodideScript.onerror = reject;
      });

      // Access loadPyodide from global scope
      const loadPyodide = (window as any).loadPyodide;
      if (!loadPyodide) {
        throw new Error('loadPyodide not found in global scope');
      }

      this.log('Setting Pyodide indexURL to: ' + PYODIDE_CDN_URL, 'debug');

      this.#pyodide = await loadPyodide({
        indexURL: PYODIDE_CDN_URL,
      });
      this.log('Pyodide core loaded.', 'info');

      this.log('Loading micropip & ghga-transpiler...', 'info');
      await this.#pyodide.loadPackage(['micropip']);
      this.#micropip = this.#pyodide.pyimport('micropip');
      this.log('Micropip loaded.', 'info');

      this.#pyodideInitialized.set(true);
    } catch (error: any) {
      const errorMsg = error.message || 'Unknown initialization error.';
      this.log(`Initialization Error: ${errorMsg}`, 'error');
      console.error(
        'FATAL: Pyodide initialization or critical package loading error:',
        error,
      );
      this.#pyodideInitialized.set(false);
    } finally {
      this.#pyodideLoading.set(false);
    }
  }

  /**
   * Writes a string to the Pyodide filesystem.
   * @param file_string - the content to write
   * @param pyodideFsPath - the absolute path in the Pyodide filesystem where to write the file
   * @returns True if successful, false otherwise
   */
  writeStringToPyodide(file_string: string, pyodideFsPath: string): boolean {
    try {
      if (!this.#pyodide?.FS) {
        this.log('Pyodide instance or FS is not available.', 'error');
        return false;
      }
      if (typeof file_string !== 'string') {
        this.log('Provided YAML content is not a string.', 'error');
        return false;
      }
      if (
        !pyodideFsPath ||
        typeof pyodideFsPath !== 'string' ||
        !pyodideFsPath.startsWith('/')
      ) {
        this.log(
          'Invalid Pyodide filesystem path provided. It must be an absolute path string (e.g., "/config/data.yaml").',
          'error',
        );
        return false;
      }

      this.log(
        `Writing string to Pyodide FS at: ${pyodideFsPath}. String length: ${file_string.length}`,
        'debug',
      );

      const dirname = pyodideFsPath.substring(0, pyodideFsPath.lastIndexOf('/'));
      if (dirname && !this.#pyodide.FS.analyzePath(dirname).exists) {
        this.#pyodide.FS.mkdirTree(dirname);
        this.log(`Created directory ${dirname} in Pyodide FS.`, 'debug');
      }

      this.#pyodide.FS.writeFile(pyodideFsPath, file_string, { encoding: 'utf8' });
      this.log(
        `String successfully written to Pyodide FS at: ${pyodideFsPath}`,
        'success',
      );
      return true;
    } catch (error: any) {
      console.error(
        `[Service] Error writing string to Pyodide FS at ${pyodideFsPath}:`,
        error,
      );
      this.log(`Error writing string to ${pyodideFsPath}: ${error.message}`, 'error');
      return false;
    }
  }

  /**
   * This function checks if a directory exists in the Pyodide filesystem,
   * and creates it if it does not exist.
   * @param path - the absolute path of the directory to check or create
   */
  checkOrCreateDirectoryInPyodideFs(path: string) {
    if (!this.#pyodideInitialized() || !this.#pyodide) {
      this.log('Pyodide not initialized.', 'error');
      return;
    }

    if (!this.#pyodide.FS.analyzePath(path).exists) {
      this.#pyodide.FS.mkdir(path);
      this.log('Created /data directory in Pyodide FS.', 'debug');
    } else {
      this.log('/data directory already exists in Pyodide FS.', 'debug');
    }
  }

  /**
   * This function checks if a given path is a valid Pyodide filesystem path.
   * It checks if Pyodide is initialized, if the path is a string, if it starts with a slash,
   * and if the path exists in the Pyodide filesystem.
   * @param path - the absolute path to check
   * @returns True if the path is valid, false otherwise
   */
  checkIfPyodideFsPathIsValid(path: string): boolean {
    if (!this.#pyodideInitialized() || !this.#pyodide) {
      this.log('Pyodide not initialized.', 'error');
      return false;
    } else if (!path || typeof path !== 'string' || !path.startsWith('/')) {
      this.log(
        'Invalid Pyodide filesystem path provided. It must be an absolute path string (e.g., "/data/input.xlsx").',
        'error',
      );
      return false;
    } else if (!this.#pyodide.FS) {
      this.log('Pyodide FS not available.', 'error');
      return false;
    } else if (!this.#pyodide.FS.analyzePath(path).exists) {
      this.log(`Path ${path} does not exist in Pyodide FS.`, 'error');
      return false;
    } else {
      return true;
    }
  }

  /**
   * This function writes a file buffer to the Pyodide filesystem.
   * It checks if Pyodide is initialized and if the filesystem is available.
   * It also checks if the provided filename is valid (absolute path).
   * @param fname - the absolute path of the file in the Pyodide filesystem
   * @param fileBuffer - the file content as an ArrayBuffer
   * @returns True if the file was successfully written, false otherwise
   */
  writeBufferToPyodideFs(fname: string, fileBuffer: ArrayBuffer): boolean {
    if (!this.#pyodideInitialized() || !this.#pyodide) {
      this.log('Pyodide not initialized.', 'error');
      return false;
    } else if (!this.#pyodide.FS) {
      this.log('Pyodide FS not available.', 'error');
      return false;
    } else if (!fname || typeof fname !== 'string' || !fname.startsWith('/')) {
      this.log(
        'Invalid filename provided. It must be an absolute path string (e.g., "/data/input.xlsx").',
        'error',
      );
      return false;
    }

    this.log(
      `Writing file to Pyodide FS at: ${fname}. Byte length: ${fileBuffer.byteLength}`,
      'debug',
    );

    const dirname = fname.substring(0, fname.lastIndexOf('/'));
    this.checkOrCreateDirectoryInPyodideFs(dirname);

    this.#pyodide.FS.writeFile(fname, new Uint8Array(fileBuffer));
    this.log(
      `FS.writeFile completed for ${fname}. Byte length: ${fileBuffer.byteLength}`,
      'debug',
    );

    const analysis = this.#pyodide.FS.analyzePath(fname);
    if (!analysis.exists || !analysis.object?.contents) {
      this.log(`${fname} NOT FOUND or empty after writing!`, 'error');
      return false;
    } else {
      this.log(`File ${fname} successfully written to Pyodide FS.`, 'success');
      return true;
    }
  }

  /**
   * This function runs a Python script in the Pyodide environment.
   * It sets the `args_js` global variable to the provided arguments,
   * and executes the script at the specified path.
   * @param script_path - the absolute path of the Python script to run in Pyodide
   * @param args - an array of arguments to pass to the script
   * @returns A promise that resolves to the result of the script execution.
   */
  async runScript(script_path: string, args: string[] = []): Promise<any> {
    if (!this.#pyodideInitialized() || !this.#pyodide) {
      this.log('Pyodide not initialized.', 'error');
      return Promise.reject(new Error('Pyodide not initialized.'));
    }

    this.log(`Running script: ${script_path} with args: ${args.join(', ')}`, 'debug');
    const script = await firstValueFrom(
      this.#http.get(script_path, { responseType: 'text' }),
    );
    this.#pyodide.globals.set('args_js', args);
    const resultProxy = await this.#pyodide.runPythonAsync(script);
    const scriptResult = Object.fromEntries(resultProxy.toJs());
    resultProxy.destroy();
    if (scriptResult['success']) {
      this.log('Python script finished successfully.', 'debug');
    } else {
      this.log(
        `Script failed: ${scriptResult['error_message'] || 'Unknown error'}`,
        'error',
      );
    }
    return scriptResult as PyodideOutput;
  }

  /**
   * Delete a file from the Pyodide filesystem if it exists.
   * @param path - the absolute path of the file to delete
   */
  async deleteFileFromPyodideFs(path: string): Promise<void> {
    if (!this.#pyodideInitialized() || !this.#pyodide) {
      this.log('Pyodide not initialized.', 'error');
      return;
    }
    if (!this.checkIfPyodideFsPathIsValid(path)) {
      this.log(`Invalid path: ${path}`, 'error');
      return;
    }
    try {
      this.#pyodide.FS.unlink(path);
      this.log(`File ${path} deleted successfully from Pyodide FS.`, 'success');
    } catch (error: any) {
      console.error(`[Service] Error deleting file from Pyodide FS at ${path}:`, error);
      this.log(`Error deleting file from ${path}: ${error.message}`, 'error');
    }
  }

  /**
   * This function resets the process log.
   */
  resetProcessLog() {
    this.#processLog.set([]);
    this.log('Process log has been reset.', 'info');
  }
}
