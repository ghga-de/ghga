/**
 * These are the unit tests for the DatePipe pipe.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { DatePipe as CommonDatePipe } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { DatePipe } from './date.pipe';

describe('DatePipe', () => {
  let pipe: DatePipe;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [CommonDatePipe, DatePipe],
    });
    pipe = TestBed.inject(DatePipe);
  });

  it('can create an instance', () => {
    expect(pipe).toBeTruthy();
  });

  it('should return null for null input', () => {
    const result = pipe.transform(null);
    expect(result).toBeNull();
  });

  it('should return null for undefined input', () => {
    const result = pipe.transform(undefined);
    expect(result).toBeNull();
  });

  it('should work with default format when no format is specified', () => {
    const date = new Date('2024-12-25');
    const result = pipe.transform(date);
    expect(result).toBe('Dec 25, 2024');
  });

  it('should work with custom format and local time zone', () => {
    const date = new Date('2024-12-25T15:30:00');
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm');
    expect(result).toBe('2024-12-25 15:30');
  });

  it('should work with custom format and UTC', () => {
    const date = new Date('2024-12-25T15:30:00Z');
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm', 'UTC');
    expect(result).toBe('2024-12-25 15:30');
  });

  it('should work with custom format and timezone offset', () => {
    const date = new Date('2024-12-25T15:30:00Z');
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm', '+01:30');
    expect(result).toBe('2024-12-25 17:00');
  });

  it('should work with custom format and negative timezone offset', () => {
    const date = new Date('2024-12-25T15:30:00Z');
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm', '-01:30');
    expect(result).toBe('2024-12-25 14:00');
  });

  it('should work with custom format and Berlin timezone', () => {
    const date = new Date('2024-12-25T15:30:00Z');
    // note that this is winter time in Berlin, so UTC+1
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm', 'Europe/Berlin');
    expect(result).toBe('2024-12-25 16:30');
  });

  it('should work with custom format and Sydney timezone', () => {
    const date = new Date('2024-12-25T15:30:00Z');
    // note that this is summer time in Sydney, so UTC+11
    const result = pipe.transform(date, 'yyyy-MM-dd HH:mm', 'Australia/Sydney');
    expect(result).toBe('2024-12-26 02:30');
  });

  it('should break if Sydney timezone is used with common pipe', () => {
    const pipe = new CommonDatePipe('en');
    const date = new Date('2024-12-25T15:30:00Z');
    let result = pipe.transform(date, 'yyyy-MM-dd HH:mm', '+11:00');
    expect(result).toBe('2024-12-26 02:30');
    result = pipe.transform(date, 'yyyy-MM-dd HH:mm', 'Australia/Sydney');
    // The following is expected to break (see
    // https://github.com/angular/angular/issues/48279).
    // If it works, it means we do not need the custom DatePipe any more.
    expect(result).not.toBe('2024-12-26 02:30');
  });
});
