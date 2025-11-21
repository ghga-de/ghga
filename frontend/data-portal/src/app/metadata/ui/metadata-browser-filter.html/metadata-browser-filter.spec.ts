/**
 * Test the metadata browser filter component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ActivatedRoute, RouterModule } from '@angular/router';
import { MetadataBrowserFilterComponent } from './metadata-browser-filter';

describe('MetadataBrowserFilterComponent', () => {
  let component: MetadataBrowserFilterComponent;
  let fixture: ComponentFixture<MetadataBrowserFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataBrowserFilterComponent],
      providers: [
        RouterModule,
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {},
          },
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MetadataBrowserFilterComponent);
    fixture.componentRef.setInput('facets', []);
    fixture.componentRef.setInput('facetData', []);
    fixture.componentRef.setInput('loading', false);
    fixture.componentRef.setInput('searchFormValue', null);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
