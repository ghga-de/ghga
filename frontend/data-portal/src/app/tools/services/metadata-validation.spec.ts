/**
 * Module containing the Transpiler tests.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { TestBed } from '@angular/core/testing';

import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Transpiler } from './transpiler';

describe('Transpiler', () => {
  let service: Transpiler;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClientTesting(), provideHttpClient()],
    });
    service = TestBed.inject(Transpiler);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
