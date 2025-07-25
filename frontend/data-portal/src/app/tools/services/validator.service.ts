/**
 * This service provides functionality to validate metadata files
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { HttpClient } from '@angular/common/http';
import { effect, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { PyodideOutput } from '../models/pyodide';
import { PyodideService } from './pyodide.service';

const YAML_SCHEMA_ASSET_PATH =
  'assets/schemas/ghga_metadata_schema.resolved.schemapack.yaml';
const SCHEMA_FILE_PATH = '/data/metadata_model.yaml';
const DEFAULT_JSON_DATAPACK_PATH = '/data/output.json';
const validatorScriptPath = '/assets/schemas/validate.py';

/**
 * This service handles the validation of metadata against a schema.
 * It uses the `schemapack` package to perform the validation.
 * It provides methods to prepare schema and JSON files and run the validator script,.
 */
@Injectable({
  providedIn: 'root',
})
export class MetadataValidationService {
  #pyodideService = inject(PyodideService);
  #http = inject(HttpClient);
  #isReady = signal(false);
  readonly log = this.#pyodideService.getProcessLog();

  constructor() {
    const eff = effect(() => {
      if (this.#pyodideService.isPyodideInitialized()) {
        this.#loadDependencies();
      }
    });
  }
  /**
   * This function loads the schemapack python package.
   */
  async #loadDependencies() {
    await this.#pyodideService.installPackage('schemapack');
    this.#isReady.set(true);
  }

  /**
   *  This function prepares a YAML schema file in the Pyodide filesystem.
   *  It fetches the YAML schema from the assets, writes it to the Pyodide filesystem,
   *  and logs the success or failure of the operation.
   * @param path - The path where the YAML schema file should be created in the Pyodide filesystem.
   */
  async prepareSchemaFileFromAssets(path: string = YAML_SCHEMA_ASSET_PATH) {
    const yamlString = await firstValueFrom(
      this.#http.get(YAML_SCHEMA_ASSET_PATH, { responseType: 'text' }),
    );

    const yamlWritten = this.#pyodideService.writeStringToPyodide(
      yamlString,
      SCHEMA_FILE_PATH,
    );
    if (yamlWritten) {
      this.#pyodideService.log(
        'Custom YAML (from asset) loaded successfully into Pyodide.',
        'success',
      );
    } else {
      this.#pyodideService.log(
        'Failed to load custom YAML (from asset) into Pyodide.',
        'error',
      );
    }
  }

  /**
   * This function prepares a JSON file in the Pyodide filesystem.
   * It writes the provided JSON content to the specified file path.
   * @param json_content - The JSON content to write to the file.
   * @param json_file_path - The path where the JSON file should be created in the Pyodide filesystem.
   */
  prepareJSONFile(
    json_content: string,
    json_file_path: string = DEFAULT_JSON_DATAPACK_PATH,
  ) {
    this.#pyodideService.writeStringToPyodide(json_content, json_file_path);
  }

  /**
   * This function runs the validator script in Pyodide. It assumes that the JSON file
   * has already been prepared in the Pyodide filesystem.
   * @param input_datapack_path - The path to the JSON file in the Pyodide filesystem.
   * @param schema_file_path - The path to the schema file in the Pyodide filesystem.
   * @returns A promise that resolves to the result of the validator script execution.
   */
  async runValidator(
    input_datapack_path: string = DEFAULT_JSON_DATAPACK_PATH,
    schema_file_path: string = SCHEMA_FILE_PATH,
  ): Promise<PyodideOutput> {
    const validatorArgs = [schema_file_path, input_datapack_path];
    const ret = await this.#pyodideService.runScript(
      validatorScriptPath,
      validatorArgs,
    );
    return ret;
  }
}
