/**
 * Test the IVA Manager List component.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { signal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute } from '@angular/router';
import { allIvas } from '@app/../mocks/data';
import { fakeActivatedRoute } from '@app/../mocks/route';
import { IvaService } from '@app/ivas/services/iva';
import { screen } from '@testing-library/angular';
import { IvaManagerList } from './iva-manager-list';

const WARN_TITLE = 'There are multiple user accounts with this name and email address.';

/**
 * Mock the IVA service as needed by the IVA Manager list component
 */
class MockIvaService {
  allIvas = { value: () => allIvas, isLoading: () => false, error: () => undefined };
  allIvasFiltered = () => this.allIvas.value();
  ambiguousUserIds = signal(new Set<string>(['jekyll@test.dev', 'hyde@test.dev']));
}

describe('IvaManagerList', () => {
  let component: IvaManagerList;
  let fixture: ComponentFixture<IvaManagerList>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [IvaManagerList],
      providers: [
        { provide: IvaService, useClass: MockIvaService },
        { provide: ActivatedRoute, useValue: fakeActivatedRoute },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(IvaManagerList);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show IVA values', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const text = compiled.textContent;
    expect(text).toContain('+441234567890004');
    expect(text).toContain(
      'c/o Weird Al Yankovic, Dr. John Doe, Wilhelmstraße 123, Apartment 25, Floor 2, 72072 Tübingen, Baden-Württemberg, Deutschland',
    );
  });

  it('should mark the IVAs of ambiguous users with a warning', () => {
    const markers = screen.getAllByTitle(WARN_TITLE);
    expect(markers).toHaveLength(2);
    for (const marker of markers) {
      expect(marker.closest('tr')).toHaveTextContent('Dr. Henry Jekyll');
    }
  });

  it('should not mark the IVAs of other users with a warning', () => {
    const rows = screen.getAllByRole('row').filter((row) => !row.closest('thead'));
    const otherRows = rows.filter((row) => !row.textContent?.includes('Henry Jekyll'));
    expect(otherRows).toHaveLength(6);
    for (const row of otherRows) {
      expect(row.querySelector(`[title="${WARN_TITLE}"]`)).toBeNull();
    }
  });
});
