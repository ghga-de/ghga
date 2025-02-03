/**
 * Test the work package creation component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { datasets } from '@app/../mocks/data';
import { Dataset } from '@app/work-packages/models/dataset';
import { WorkPackageService } from '@app/work-packages/services/work-package.service';
import { WorkPackageComponent } from './work-package.component';

import { screen } from '@testing-library/angular';

/**
 * Mock the work package service as needed for the work package component
 */
class MockWorkPackageService {
  datasets = signal<Dataset[]>(datasets);
  datasetsAreLoading = signal<boolean>(false);
  datasetsError = signal<unknown>(undefined);
}

describe('WorkPackageComponent', () => {
  let component: WorkPackageComponent;
  let fixture: ComponentFixture<WorkPackageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WorkPackageComponent, NoopAnimationsModule],
      providers: [{ provide: WorkPackageService, useClass: MockWorkPackageService }],
    }).compileComponents();

    fixture = TestBed.createComponent(WorkPackageComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show proper heading', () => {
    const heading = screen.getByRole('heading');
    expect(heading).toHaveTextContent('Download or upload datasets');
  });

  it('should show dataset selector', async () => {
    const select = screen.getByLabelText('Available datasets');
    expect(select).toBeTruthy();
    select.click();
    await fixture.whenStable();
    const option = screen.getByText('GHGAD588887987: Some dataset to upload');
    expect(option).toBeTruthy();
  });
});
