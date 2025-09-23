/**
 * This component acts as a frontend for the validation service
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { CommonModule } from '@angular/common';
import { Component, effect, inject, signal, WritableSignal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { LogEntry, PyodideOutput } from '@app/tools/models/pyodide';
import { StepDetails, StepStatus } from '@app/tools/models/stepper';
import { PyodideService } from '@app/tools/services/pyodide.service';
import { MetadataValidationService } from '@app/tools/services/validator.service';
import { FormatSchemapackErrorPipe } from '../../pipes/schemapack-error.pipe';
import { TranspilerService } from '../../services/transpiler.service';
import { StepperComponent } from '../stepper/stepper.component';

/**
 * This component works in tandem with the MetadataValidationService to provide
 * a user interface for validating metadata files.
 * It allows users to drag and drop or select XLSX files, which are then
 * processed to JSON format and validated against a schema.
 */
@Component({
  selector: 'app-metadata-validator',
  templateUrl: './metadata-validator.component.html',
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    StepperComponent,
    FormatSchemapackErrorPipe,
  ],
})
export class MetadataValidatorComponent {
  #validationService = inject(MetadataValidationService);
  #transpilerService = inject(TranspilerService);
  #pyodideService = inject(PyodideService);
  statusText: WritableSignal<string> = signal('Initializing...');
  isStatusError: WritableSignal<boolean> = signal(false);
  errorText: WritableSignal<string> = signal('');
  showSpinner: WritableSignal<boolean> = signal(true);
  isDragOver: WritableSignal<boolean> = signal(false);
  fileName: WritableSignal<string> = signal('');
  jsonOutput: WritableSignal<string> = signal('Awaiting XLSX file...');
  processLogEntries: WritableSignal<LogEntry[]> = signal([]);
  showLog: WritableSignal<boolean> = signal(false);
  processButtonEnabled: WritableSignal<boolean> = signal(false);
  validationOutputDetails: WritableSignal<string | null> = signal(null);

  stepDetails: WritableSignal<StepDetails[]> = signal([
    { name: 'File Selection', status: 'idle' },
    { name: 'Transpilation', status: 'idle' },
    { name: 'Validation', status: 'idle' },
  ]);

  #fileBuffer: ArrayBuffer | null = null;

  // Effect to handle Pyodide initialization status
  #pyodideStatusEffect = effect(() => {
    const isReady = this.#pyodideService.isPyodideInitialized();
    const isLoading = this.#pyodideService.isPyodideLoading();

    if (isLoading) {
      this.#updateStatus('Loading Pyodide runtime...', false, true);
      this.#resetStepStatus();
    } else if (isReady) {
      this.#updateStatus('ghga-transpiler ready.', false, false);
      this.#resetStepStatus();
      this.processButtonEnabled.set(this.#fileBuffer !== null);
    } else {
      this.#updateStatus('Pyodide initialization failed.', true, false);
      this.processButtonEnabled.set(false);
      this.stepDetails.update((steps) => {
        steps[0].status = 'failed';
        return steps;
      });
    }
  });

  // Effect to handle process log updates from the service
  #processLogEffect = effect(() => {
    this.processLogEntries.set(this.#pyodideService.getProcessLog());
    // Scroll to bottom of log if it's visible, ensure this runs after DOM update
    setTimeout(() => {
      const logContainer = document.getElementById('processLog');
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight;
      }
    }, 0);
  });

  /**
   * Resets all step statuses to 'idle'.
   */
  #resetStepStatus(): void {
    this.stepDetails.update((steps) =>
      steps.map((step) => ({ ...step, status: 'idle' })),
    );
  }

  /**
   * Sets the status of a specific step.
   * @param step_index The index of the step to update.
   * @param status The new status.
   */
  #setStepStatus(step_index: number, status: StepStatus): void {
    this.stepDetails.update((steps) => {
      if (step_index < 0 || step_index >= steps.length) {
        console.warn(`Invalid step index: ${step_index}`);
        return steps;
      }
      steps[step_index].status = status;
      return steps;
    });
  }

  /**
   * Updates the status display in the UI using signals.
   * @param message The status message.
   * @param isError Whether the message indicates an error.
   * @param keepSpinner Whether to keep the spinner visible.
   */
  #updateStatus(message: string, isError: boolean, keepSpinner: boolean): void {
    this.statusText.set(message);
    this.isStatusError.set(isError);
    this.errorText.set(isError ? message : '');
    this.showSpinner.set(keepSpinner);
  }

  /**
   * Handles drag over event for the drop area.
   * @param event DragEvent
   */
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(true);
  }

  /**
   * Handles drag leave event for the drop area.
   * @param event DragEvent
   */
  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
  }

  /**
   * Handles drop event for the drop area.
   * @param event DragEvent
   */
  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver.set(false);
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.#handleFile(files[0]);
    }
  }

  /**
   * Handles file selection via input.
   * @param event Event
   */
  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = input.files;
    if (files && files.length > 0) {
      this.#handleFile(files[0]);
    }
  }

  /**
   * Processes the selected file.
   * @param file The File object.
   */
  #handleFile(file: File): void {
    this.jsonOutput.set('Awaiting XLSX file...'); // Set initial message for pre tag
    this.validationOutputDetails.set(null); // Clear previous validation errors

    this.#setStepStatus(0, 'ongoing');
    this.#setStepStatus(1, 'idle');
    this.#setStepStatus(2, 'idle');

    if (!file || !file.name.endsWith('.xlsx')) {
      const msg = 'Please select a valid .xlsx file.';
      this.#updateStatus(msg, true, false);
      this.fileName.set('');
      this.#fileBuffer = null;
      this.processButtonEnabled.set(false);
      this.#setStepStatus(0, 'failed');
      return;
    }

    this.fileName.set(`Selected: ${file.name}`);
    const reader = new FileReader();

    reader.onload = (e) => {
      this.#fileBuffer = e.target?.result as ArrayBuffer;
      const msg = `File "${file.name}" loaded. Ready to transpile.`;
      this.#updateStatus(msg, false, false);
      this.#setStepStatus(0, 'succeeded');
      // Enable button only if Pyodide is initialized and a file is loaded
      this.processButtonEnabled.set(this.#pyodideService.isPyodideInitialized());
      this.jsonOutput.set('Ready for transpilation...'); // Update pre tag
    };

    reader.onerror = (e) => {
      const msg = `Error reading file: ${e.target?.error?.name}`;
      this.#updateStatus(msg, true, false);
      this.#fileBuffer = null;
      this.processButtonEnabled.set(false);
      this.#setStepStatus(0, 'failed');
    };

    reader.readAsArrayBuffer(file);
  }

  /**
   * Initiates the transpilation process.
   */
  async transpileFile(): Promise<void> {
    if (!this.#fileBuffer) {
      const msg = 'No file selected to transpile.';
      this.#updateStatus(msg, true, false);
      this.#setStepStatus(1, 'failed');
      return;
    }

    this.#updateStatus('Transpiling XLSX to JSON...', false, true);
    this.processButtonEnabled.set(false);
    this.jsonOutput.set('Processing...'); // Update pre tag
    this.validationOutputDetails.set(null); // Clear validation output when starting a new transpile

    this.#setStepStatus(1, 'ongoing');
    this.#setStepStatus(2, 'idle'); // Reset validation step

    try {
      const transpilerResult: PyodideOutput =
        await this.#transpilerService.runTranspiler(this.#fileBuffer);

      if (transpilerResult.success && transpilerResult.json_output !== null) {
        this.jsonOutput.set(transpilerResult.json_output);

        this.#setStepStatus(1, 'succeeded');
        this.#setStepStatus(2, 'ongoing');
      } else {
        const errorMsg =
          transpilerResult.error_message ||
          'Unknown transpilation error or no JSON output.';
        this.jsonOutput.set(`Transpilation Failed. See process log.`);
        this.#updateStatus(
          'Transpilation failed. Check process log and console.',
          true,
          false,
        );
        this.#setStepStatus(1, 'failed');
        this.#setStepStatus(2, 'failed');
        this.validationOutputDetails.set(null);
        return;
      }

      // If transpilation was successful, proceed to validation

      await this.#validationService.prepareSchemaFileFromAssets();

      const validationResult = await this.#validationService.runValidator();

      if (validationResult.success !== undefined) {
        if (validationResult.success) {
          this.#pyodideService.log('Schema validation successful!', 'success');
          this.#setStepStatus(2, 'succeeded');
          this.#updateStatus('Transpilation and validation successful!', false, false);

          if (validationResult.output && validationResult.output.trim()) {
            this.#pyodideService.log(
              `Validation Output:\n${validationResult.output.trim()}`,
              'info',
            );
          }

          if (validationResult.error_message && validationResult.error_message.trim()) {
            this.#pyodideService.log(
              `Validation Info/Warnings:\n${validationResult.error_message.trim()}`,
              'info',
            );
            this.validationOutputDetails.set(validationResult.error_message);
          }
        } else {
          this.#setStepStatus(2, 'failed');
          this.#pyodideService.log('Schema validation FAILED.', 'error');
          this.#updateStatus(
            'Transpilation successful, but validation failed.',
            true,
            false,
          );

          let combinedValidationError = '';
          if (validationResult.output && validationResult.output.trim()) {
            combinedValidationError += `Validation Output (stdout):\n${validationResult.output.trim()}\n\n`;
            this.#pyodideService.log(
              `Validation Output (stdout):\n${validationResult.output.trim()}`,
              'info',
            );
          }
          if (validationResult.error_message && validationResult.error_message.trim()) {
            combinedValidationError += `Validation Errors (stderr):\n${validationResult.error_message.trim()}`;
            this.#pyodideService.log(
              `Validation Errors (stderr):\n${validationResult.error_message.trim()}`,
              'error',
            );
          } else {
            combinedValidationError +=
              'No specific error message from validation. Check console.';
            this.#pyodideService.log(
              'No specific error message from validation. Check console.',
              'error',
            );
          }
          this.validationOutputDetails.set(combinedValidationError.trim());
        }
      } else {
        this.#pyodideService.log(
          'Validation was not performed (likely due to prior transpilation issues).',
          'info',
        );
        this.#setStepStatus(2, 'idle');
        this.#updateStatus(
          'Transpilation successful, validation skipped.',
          false,
          false,
        );
      }
    } catch (error: any) {
      const errorMsg =
        error.message || 'An unexpected error occurred during transpilation.';
      this.jsonOutput.set(`Transpilation Error: ${errorMsg}`);
      this.#updateStatus(`Transpilation Error. ${errorMsg}`, true, false);
      this.#setStepStatus(1, 'failed');
      this.#setStepStatus(2, 'failed');
      this.validationOutputDetails.set(null);
    } finally {
      this.processButtonEnabled.set(true);
    }
  }

  /**
   * Initiates download of the current JSON output.
   */
  downloadJson(): void {
    const jsonContent = this.jsonOutput();
    if (
      !jsonContent ||
      jsonContent === 'Awaiting XLSX file...' ||
      jsonContent === 'Processing...' ||
      jsonContent.startsWith('Transpilation ')
    ) {
      return;
    }

    const blob = new Blob([jsonContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'output.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  /**
   * Toggles the visibility of the process log.
   */
  toggleLog(): void {
    this.showLog.update((currentValue) => !currentValue);
  }
}
