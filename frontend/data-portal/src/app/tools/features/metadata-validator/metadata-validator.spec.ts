/**
 * Test the Metadata Validator component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { LogEntry } from '@app/tools/models/pyodide';
import { PyodideService } from '@app/tools/services/pyodide';
import { TranspilerService } from '@app/tools/services/transpiler';
import { MetadataValidationService } from '@app/tools/services/validator';
import { screen } from '@testing-library/angular';
import { MetadataValidatorComponent } from './metadata-validator';

/**
 * Mock the Pyodide service, so that no Python runtime is loaded
 */
class MockPyodideService {
  isPyodideInitialized = signal(true);
  isPyodideLoading = signal(false);
  processLog = signal<LogEntry[]>([]);
  getProcessLog = this.processLog.asReadonly();
}

describe('MetadataValidatorComponent', () => {
  let fixture: ComponentFixture<MetadataValidatorComponent>;
  let pyodide: MockPyodideService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataValidatorComponent],
      providers: [
        { provide: PyodideService, useClass: MockPyodideService },
        { provide: MetadataValidationService, useValue: {} },
        { provide: TranspilerService, useValue: {} },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MetadataValidatorComponent);
    pyodide = TestBed.inject(PyodideService) as unknown as MockPyodideService;
    await fixture.whenStable();
  });

  it('should report that the transpiler is ready', () => {
    expect(screen.getByText('ghga-transpiler ready.')).toBeVisible();
  });

  it('should show the entries of the process log as they come in', async () => {
    pyodide.processLog.set([
      { message: 'Loading packages', type: 'info', time: '10:00:00' },
    ]);
    await fixture.whenStable();
    expect(screen.getByText('Loading packages')).toBeInTheDocument();

    pyodide.processLog.update((log) => [
      ...log,
      { message: 'Validation failed', type: 'error', time: '10:00:01' },
    ]);
    await fixture.whenStable();
    expect(screen.getByText('Loading packages')).toBeInTheDocument();
    expect(screen.getByText('Validation failed')).toHaveClass('text-red-500');
  });
});
