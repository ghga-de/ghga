import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConfirmTotpComponent } from './confirm-totp.component';

describe('ConfirmTotpComponent', () => {
  let component: ConfirmTotpComponent;
  let fixture: ComponentFixture<ConfirmTotpComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ConfirmTotpComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(ConfirmTotpComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
