import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetadataBrowserComponent } from './metadata-browser.component';

describe('BrowseComponent', () => {
  let component: MetadataBrowserComponent;
  let fixture: ComponentFixture<MetadataBrowserComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataBrowserComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(MetadataBrowserComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
