/**
 * Module containing the TranspilerService tests.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TranspilerService } from './transpiler.service';

describe('TranspilerService', () => {
  let service: TranspilerService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClientTesting(), provideHttpClient()],
    });
    service = TestBed.inject(TranspilerService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
