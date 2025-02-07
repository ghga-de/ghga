/**
 * Test the version ribbon component
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ConfigService } from '@app/shared/services/config.service';
import { VersionRibbonComponent } from './version-ribbon.component';

/**
 * Mock the config service as needed by the version ribbon component
 */
class MockConfigService {
  ribbonText = 'Test ribbon text';
}

describe('VersionRibbonComponent', () => {
  let component: VersionRibbonComponent;
  let fixture: ComponentFixture<VersionRibbonComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [VersionRibbonComponent],
      providers: [{ provide: ConfigService, useClass: MockConfigService }],
    }).compileComponents();

    fixture = TestBed.createComponent(VersionRibbonComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show the ribbon text', () => {
    const text = fixture.nativeElement.textContent;
    expect(text).toBe('Test ribbon text');
  });

  it('should remove the ribbon text on click', async () => {
    const element = fixture.nativeElement;
    let aside = element.querySelector('aside');
    expect(aside).toBeTruthy();
    expect(aside.textContent).toBe('Test ribbon text');
    aside.click();
    await fixture.whenStable();
    aside = element.querySelector('aside');
    expect(aside).toBeFalsy();
    expect(element.textContent).toBe('');
  });
});
