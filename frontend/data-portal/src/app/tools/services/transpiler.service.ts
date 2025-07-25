/**
 * This service provides functionality to transpile metadata files
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { effect, inject, Injectable, signal, WritableSignal } from '@angular/core';
import { PyodideOutput } from '../models/pyodide';
import { PyodideService } from './pyodide.service';

const INPUT_FILE_PATH = '/data/input.xlsx';
const OUTPUT_FILE_PATH = '/data/output.json';
const transpilerScriptPath = '/assets/schemas/transpile.py';

/**
 * This service handles the transpilation of metadata.
 */
@Injectable({
  providedIn: 'root',
})
export class TranspilerService {
  #pyodideService = inject(PyodideService);
  #isReady: WritableSignal<boolean> = signal(false);

  constructor() {
    const eff = effect(() => {
      if (this.#pyodideService.isPyodideInitialized()) {
        this.#loadDependencies();
      }
    });
  }

  /**
   * This function loads the transpiler python package.
   */
  async #loadDependencies() {
    await this.#pyodideService.installPackage('ghga-transpiler');
    this.#isReady.set(true);
  }

  /**
   * This executes the transpiler script in Pyodide.
   * It deletes possible old outputs, writes the input file to the Pyodide filesystem, runs the transpiler script,
   * and returns the result.
   * @param file - The input file as an ArrayBuffer.
   * @returns A promise that resolves to the result of the transpiler script execution.
   */
  async runTranspiler(file: ArrayBuffer): Promise<PyodideOutput> {
    await this.#pyodideService.deleteFileFromPyodideFs(OUTPUT_FILE_PATH);
    this.#pyodideService.writeBufferToPyodideFs(INPUT_FILE_PATH, file);
    const transpilerArgs = [INPUT_FILE_PATH, OUTPUT_FILE_PATH];
    return await this.#pyodideService.runScript(transpilerScriptPath, transpilerArgs);
  }
}
