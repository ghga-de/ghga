/**
 * Test the Schemapack Playground component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PyodideOutput } from '@app/tools/models/pyodide';
import { PyodideLoader } from '@app/tools/services/pyodide';
import { MetadataValidationService } from '@app/tools/services/validator';
import { screen, waitFor } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { SchemapackPlayground } from './schemapack-playground';

/**
 * Mock the Pyodide service, so that no Python runtime is loaded
 */
class MockPyodideService {
  resetProcessLog = vitest.fn();
  writeStringToPyodide = vitest.fn();
}

/**
 * Mock the validation service, which would run schemapack in Pyodide
 */
class MockMetadataValidationService {
  runValidator = vitest.fn(async (): Promise<PyodideOutput> => ({
    success: true,
    json_output: null,
    error_message: null,
  }));
}

describe('SchemapackPlayground', () => {
  let fixture: ComponentFixture<SchemapackPlayground>;
  let pyodide: MockPyodideService;
  let validator: MockMetadataValidationService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SchemapackPlayground],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: PyodideLoader, useClass: MockPyodideService },
        { provide: MetadataValidationService, useClass: MockMetadataValidationService },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SchemapackPlayground);
    pyodide = TestBed.inject(PyodideLoader) as unknown as MockPyodideService;
    validator = TestBed.inject(
      MetadataValidationService,
    ) as unknown as MockMetadataValidationService;
    await fixture.whenStable();
  });

  /**
   * Enter a schema and data into the two text areas
   * @param schema - the YAML schema to enter
   * @param data - the JSON data to enter
   */
  async function enter(schema: string, data: string) {
    await userEvent.click(
      screen.getByRole('textbox', { name: 'Paste your YAML schema here' }),
    );
    await userEvent.paste(schema);
    await userEvent.click(
      screen.getByRole('textbox', { name: 'Paste your JSON data here' }),
    );
    await userEvent.paste(data);
  }

  it('should validate the entered schema and data', async () => {
    await enter('schemapack: 4.0.0', '{"datapack": "4.0.0"}');
    await userEvent.click(screen.getByRole('button', { name: 'Validate' }));
    await fixture.whenStable();

    expect(pyodide.writeStringToPyodide).toHaveBeenCalledWith(
      'schemapack: 4.0.0',
      '/playground/schema.yaml',
    );
    expect(pyodide.writeStringToPyodide).toHaveBeenCalledWith(
      '{"datapack": "4.0.0"}',
      '/playground/data.json',
    );
    expect(validator.runValidator).toHaveBeenCalledOnce();
    expect(screen.getByText('Validation successful. No issues found.')).toBeVisible();
  });

  it('should show the details when the validation fails', async () => {
    validator.runValidator.mockResolvedValueOnce({
      success: false,
      json_output: null,
      error_message: 'Missing class Dataset',
    });
    await enter('schemapack: 4.0.0', '{}');
    await userEvent.click(screen.getByRole('button', { name: 'Validate' }));
    await fixture.whenStable();

    expect(
      screen.getByText('Validation failed. Check the details below.'),
    ).toBeVisible();
    expect(screen.getByText('Missing class Dataset')).toBeVisible();
  });

  it('should reject data that is not JSON without running the validator', async () => {
    await enter('schemapack: 4.0.0', 'not json');
    await userEvent.click(screen.getByRole('button', { name: 'Validate' }));
    await fixture.whenStable();

    expect(
      screen.getByText('Invalid JSON data. Please check your input.'),
    ).toBeVisible();
    expect(validator.runValidator).not.toHaveBeenCalled();
  });

  it('should load the default example into the text areas', async () => {
    await userEvent.click(screen.getByRole('button', { name: 'Load Default Example' }));
    TestBed.inject(HttpTestingController)
      .expectOne('assets/schemas/demo_schema.schemapack.yaml')
      .flush('schemapack: 4.0.0\n');
    await waitFor(() =>
      expect(
        screen.getByRole('textbox', { name: 'Paste your YAML schema here' }),
      ).toHaveValue('schemapack: 4.0.0\n'),
    );
    const data = screen.getByRole('textbox', { name: 'Paste your JSON data here' });
    expect(JSON.parse((data as HTMLTextAreaElement).value)).toMatchObject({
      datapack: '4.0.0',
    });
    expect(
      screen.getByText('Default example loaded. Ready to validate.'),
    ).toBeVisible();
  });
});
