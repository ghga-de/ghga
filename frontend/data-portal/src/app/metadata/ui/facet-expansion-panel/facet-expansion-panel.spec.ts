/**
 * Short module description
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';
import { FacetExpansionPanelComponent } from './facet-expansion-panel';

describe('FacetExpansionPanelComponent', () => {
  let component: FacetExpansionPanelComponent;
  let fixture: ComponentFixture<FacetExpansionPanelComponent>;
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [FacetExpansionPanelComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(FacetExpansionPanelComponent);
    fixture.componentRef.setInput('facet', {
      key: 'test',
      name: 'Test Facet',
      options: [
        { count: 2, value: 'Test_Option_1' },
        { count: 7, value: 'Test_Option_2' },
        { count: 1, value: 'All_Tests' },
      ],
    });
    fixture.componentRef.setInput('selectedOptions', [
      'Test_Option_3',
      'Test_Option_2',
    ]);
    fixture.componentRef.setInput('expanded', true);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should have the correct number of options (3 in the facet object + 1 selected not in the facet object)', () => {
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBe(4);
  });

  it('should be expanded from the start', () => {
    const expansionPanelButton = screen.getByRole('button', {
      name: 'Test Facet(4)',
    });
    expect(expansionPanelButton.parentElement?.className.includes('mat-expanded')).toBe(
      true,
    );
  });

  it('should sort the options alphabetically', () => {
    const checkboxes = screen.getAllByRole('checkbox');
    const checkBoxNames = checkboxes.map((x) => x.getAttribute('name')?.slice(5));
    expect(checkBoxNames).toStrictEqual([
      'All_Tests',
      'Test_Option_1',
      'Test_Option_2',
      'Test_Option_3',
    ]);
  });

  it('should keep the sort order of the selected mat chips', () => {
    const generics = screen.getAllByRole('generic');
    const matChipValues = generics
      .filter((x) => x.className.includes('mat-mdc-chip-action-label'))
      .map((x) => x.textContent.trim());
    expect(matChipValues).toStrictEqual(['Test Option 2', 'Test Option 3']);
  });

  it('should emit events correctly when de-/selecting an option', async () => {
    let selected = false;
    const checkboxes = screen.getAllByRole('checkbox');
    const checkbox = checkboxes.find(
      (x) => x.getAttribute('name') === 'test#Test_Option_1',
    );
    expect(checkbox).toBeTruthy();
    component.optionSelected.subscribe((x) => (selected = x.checked));
    await userEvent.click(checkbox!);
    expect(selected).toBe(true);
    await userEvent.click(checkbox!);
    expect(selected).toBe(false);
  });

  it('should emit events correctly when removing an option via the chips', async () => {
    let emitted: string | undefined;
    const button = screen.getByRole('button', {
      name: 'Remove filter for Test Option 2',
    });
    expect(button).toBeTruthy();
    component.optionRemoved.subscribe((x) => (emitted = x));
    await userEvent.click(button);
    expect(emitted).toBe('test#Test_Option_2');
  });

  it('should emit events correctly when closing the expansion panel', async () => {
    let emitted: boolean | undefined;
    component.panelExpansionChanged.subscribe((x) => (emitted = x));
    const button = screen.getByRole('button', {
      name: 'Test Facet(4)',
    });
    expect(button).toBeTruthy();
    expect(button.parentElement?.className.includes('mat-expanded')).toBe(true);
    await userEvent.click(button);
    expect(button.parentElement?.className.includes('mat-expanded')).toBe(false);
    expect(emitted).toBe(false);
  });
});
