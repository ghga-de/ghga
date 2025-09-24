/**
 * This component is a Schemapack Playground for validating metadata files.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { PyodideOutput } from '@app/tools/models/pyodide';
import { SchemapackOutputStatus } from '@app/tools/models/status-text';
import { PyodideService } from '@app/tools/services/pyodide.service';
import { MetadataValidationService } from '@app/tools/services/validator.service';
import { firstValueFrom } from 'rxjs';
import { FormatSchemapackErrorPipe } from '../../pipes/schemapack-error.pipe';
import { StatusTextBoxComponent } from '../status-text-box/status-text-box.component';

const PLAYGROUND_SCHEMA_PYODIDE_PATH = '/playground/schema.yaml';
const PLAYGROUND_JSON_PYODIDE_PATH = '/playground/data.json';
const PLAYGROUND_SCHEMA_ASSET_PATH = 'assets/schemas/demo_schema.schemapack.yaml';
const PLAYGROUND_DEMO_JSON_VALUE =
  '{"datapack":"4.0.0","resources":{"File":{"file_a":{"content":{"filename":"file_a.fastq","format":"FASTQ","checksum":"1a5ac10ab42911dc0224172c118a326d9a4c03969112a2f3eb1ad971e96e92b8","size":12321}},"file_b":{"content":{"filename":"file_b.fastq","format":"FASTQ","checksum":"2b5ac10ab42911dc0224172c118a326d9a4c03969112a2f3eb1ad971e96e92c9","size":12314}},"file_c":{"content":{"filename":"file_c.fastq","format":"FASTQ","checksum":"a9c24870071da03f78515e6197048f3a2172e90e597e9250cd01a0cb8f0986ed","size":12123}}},"Dataset":{"dataset_1":{"content":{"dac_contact":"dac@example.org"},"relations":{"files":{"targetClass":"File","targetResources":["file_a","file_b","file_c"]}}}},"Sample":{"sample_x":{"content":{"description":"Some sample."},"relations":{"files":{"targetClass":"File","targetResources":["file_a","file_b"]}}},"sample_y":{"content":{},"relations":{"files":{"targetClass":"File","targetResources":["file_c"]}}}},"Experiment":{"experiment_i":{"content":{},"relations":{"samples":{"targetClass":"Sample","targetResources":["sample_x","sample_y"]}}}}}}';

/**
 * This component uses schemapack to validate metadata files. It serves as a demo for that library.
 */
@Component({
  selector: 'app-schemapack-playground',
  templateUrl: './schemapack-playground.component.html',
  imports: [
    CommonModule,
    MatButtonModule,
    FormsModule,
    MatIconModule,
    FormatSchemapackErrorPipe,
    StatusTextBoxComponent,
  ],
})
export class SchemapackPlaygroundComponent {
  #validationService = inject(MetadataValidationService);
  #pyodideService = inject(PyodideService);
  #http = inject(HttpClient);
  schemaYaml = signal<string>('');
  jsonData = signal<string>('');
  defaultSchema = '';
  isStatusError = signal<boolean>(false);
  showSpinner = signal<boolean>(false);
  validationDetails = signal<string | null>(null);
  statusText = signal<string>('Ready. Load a default or paste your content.');
  status = signal<SchemapackOutputStatus>(SchemapackOutputStatus.READY);

  /**
   * Loads the default schema and JSON data into the text areas.
   */
  async loadDefault() {
    this.status.set(SchemapackOutputStatus.LOADING);
    this.defaultSchema = await firstValueFrom(
      this.#http.get(PLAYGROUND_SCHEMA_ASSET_PATH, { responseType: 'text' }),
    );
    this.schemaYaml.set(this.defaultSchema);
    this.jsonData.set(JSON.stringify(JSON.parse(PLAYGROUND_DEMO_JSON_VALUE), null, 2));
    this.statusText.set('Default example loaded. Ready to validate.');
    this.isStatusError.set(false);
    this.validationDetails.set(null);
    this.status.set(SchemapackOutputStatus.READY);
  }

  /**
   * This function starts the validation process.
   */
  async validate(): Promise<void> {
    try {
      const ret = JSON.parse(this.jsonData());
    } catch (error) {
      this.statusText.set('Invalid JSON data. Please check your input.');
      this.isStatusError.set(true);
      this.validationDetails.set(
        (error as Error).message.replace('JSON.parse: ', 'Error: '),
      );
      this.status.set(SchemapackOutputStatus.ERROR);
      return;
    }
    this.status.set(SchemapackOutputStatus.LOADING);
    this.showSpinner.set(true);
    this.isStatusError.set(false);
    this.validationDetails.set(null);

    this.#pyodideService.resetProcessLog();
    this.#pyodideService.writeStringToPyodide(
      this.schemaYaml(),
      PLAYGROUND_SCHEMA_PYODIDE_PATH,
    );
    this.#pyodideService.writeStringToPyodide(
      this.jsonData(),
      PLAYGROUND_JSON_PYODIDE_PATH,
    );

    const result: PyodideOutput = await this.#validationService.runValidator(
      PLAYGROUND_JSON_PYODIDE_PATH,
      PLAYGROUND_SCHEMA_PYODIDE_PATH,
    );
    this.status.set(
      result.success ? SchemapackOutputStatus.SUCCESS : SchemapackOutputStatus.ERROR,
    );
    if (!result.success) {
      this.statusText.set('Validation failed. Check the details below.');
      this.isStatusError.set(true);
      this.validationDetails.set(result.error_message);
    } else {
      this.statusText.set('Validation successful. No issues found.');
    }

    this.showSpinner.set(false);
  }
}
