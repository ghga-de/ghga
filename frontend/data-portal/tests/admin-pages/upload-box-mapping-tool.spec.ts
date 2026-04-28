/**
 * Playwright test for Upload Box mapping tool in Upload Box manager detail view.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'Upload Box Manager',
  adminMenuItemUrl: '/upload-box-manager',
});

test('can map files and archive locked upload box using mapping tool', async ({
  adminPage: page,
}) => {
  await expectTitle(page, 'Upload Box Manager');

  const main = page.locator('main');

  const filterToggle = page.getByRole('button', { name: 'Filter upload boxes' });
  if (await filterToggle.isVisible()) {
    await filterToggle.click();
  }

  const titleFilter = main.getByLabel('Upload box title').first();
  await expect(titleFilter).toBeVisible();
  await titleFilter.fill('Research Data Upload Box of Jane');

  const detailsButton = main
    .getByRole('button', { name: 'View upload box details' })
    .first();
  await expect(detailsButton).toBeVisible();
  await detailsButton.click();

  await expect(page).toHaveURL(/\/upload-box-manager\/.+/);
  await expectTitle(page, 'Upload Box Details');

  const detailsMain = page.locator('main');
  const uploadBoxInfoHeading = detailsMain.getByRole('heading', {
    level: 2,
    name: 'Upload Box Info',
  });
  await expect(uploadBoxInfoHeading).toBeVisible();

  const uploadBoxInfoCard = page.locator('mat-card').filter({
    has: page.getByRole('heading', { level: 2, name: 'Upload Box Info' }),
  });
  await expect(uploadBoxInfoCard).toContainText('Research Data Upload Box of Jane');
  await expect(uploadBoxInfoCard).toContainText('State:');
  await expect(uploadBoxInfoCard).toContainText('Locked');

  const storageCard = page.locator('mat-card').filter({
    has: page.getByRole('heading', { level: 2, name: 'Storage & Files' }),
  });
  await expect(storageCard).toBeVisible();

  const storageTable = storageCard.locator('table');
  await expect(
    storageTable.getByRole('columnheader', { name: 'Accession' }),
  ).toHaveCount(0);

  const methStorageRow = storageTable
    .locator('tr')
    .filter({ hasText: 'methylation_sample_001.meth' })
    .first();
  await expect(methStorageRow).toBeVisible();
  await expect(methStorageRow).toContainText('interrogated');
  await expect(methStorageRow).toContainText('2 GB');

  const studyCard = page.locator('mat-card').filter({
    has: page.getByRole('heading', { level: 2, name: 'Study' }),
  });
  await expect(studyCard).toBeVisible();
  await expect(studyCard).toContainText(
    'Please select the study corresponding to this upload box',
  );

  const studySelector = studyCard.getByRole('combobox').first();
  await expect(studySelector).toBeVisible();
  await studySelector.click();

  const testStudyOption = page.getByRole('option', {
    name: 'GHGAS99999999999001: Upload Box File Mapping Test Study',
  });
  await expect(testStudyOption).toBeVisible();
  await testStudyOption.click();

  const mappingCard = page.locator('mat-card').filter({
    has: page.getByRole('heading', { level: 2, name: 'File Mapping' }),
  });
  await expect(mappingCard).toBeVisible();

  const aliasRadio = mappingCard.getByRole('radio', { name: 'File alias' });
  await expect(aliasRadio).toBeVisible();
  await aliasRadio.check();

  await expect(mappingCard).toContainText('Files in Experimental Metadata: 16');
  await expect(mappingCard).toContainText('Files in Upload Box: 15');
  await expect(mappingCard).toContainText('Unmapped: 2');
  await expect(mappingCard).toContainText('Unmapped: 1');

  await expect(mappingCard.getByText('some_unessential_data.csv')).toBeVisible();
  await expect(mappingCard.getByText('methylation_data.meth')).toHaveCount(0);

  const nextPageButton = mappingCard.getByRole('button', { name: 'Next page' });
  await expect(nextPageButton).toBeVisible();
  await nextPageButton.click();

  const methMetadataRow = mappingCard
    .locator('tr')
    .filter({ hasText: 'methylation_data.meth' })
    .first();
  await expect(methMetadataRow).toBeVisible();
  await expect(methMetadataRow).toContainText('unmapped');

  const confirmMappingButton = mappingCard.getByRole('button', {
    name: 'Confirm mapping and archive',
  });
  await expect(confirmMappingButton).toBeVisible();
  await confirmMappingButton.click();

  const confirmDialog = page.getByRole('dialog');
  await expect(confirmDialog).toBeVisible();
  await expect(confirmDialog).toContainText('methylation_sample_001.meth');
  await expect(confirmDialog).toContainText('methylation_data.meth');
  await expect(confirmDialog.getByRole('button', { name: 'Cancel' })).toBeVisible();
  await expect(
    confirmDialog.getByRole('button', { name: 'Confirm and Archive' }),
  ).toHaveCount(0);
  await confirmDialog.getByRole('button', { name: 'Cancel' }).click();

  const setMappingButton = mappingCard.getByRole('button', {
    name: 'Click to set mapping for methylation_data.meth',
  });
  await expect(setMappingButton).toBeVisible();
  await setMappingButton.click();

  const inlineMappingInput = mappingCard.getByRole('combobox', {
    name: 'Map upload box file for methylation_data.meth',
  });
  await expect(inlineMappingInput).toBeVisible();
  await inlineMappingInput.fill('methylation_sample_001.meth');

  const inlineMappingOption = page.getByRole('option', {
    name: 'methylation_sample_001.meth',
  });
  await expect(inlineMappingOption).toBeVisible();
  await inlineMappingOption.click();

  await expect(mappingCard).toContainText('Mapped: 15');
  await expect(mappingCard).toContainText('Unmapped: 1');
  await expect(mappingCard).toContainText('Matches: 14');
  await expect(mappingCard).toContainText('Manual: 1');

  await confirmMappingButton.click();

  const finalConfirmDialog = page.getByRole('dialog', {
    name: 'Confirm Mapping and Archive',
  });
  await expect(finalConfirmDialog).toBeVisible();
  await expect(finalConfirmDialog).not.toContainText(
    'The following file in the upload box has not been mapped:',
  );
  await expect(finalConfirmDialog).toContainText('some_unessential_data.csv');

  const cancelButton = finalConfirmDialog.getByRole('button', { name: 'Cancel' });
  const confirmArchiveButton = finalConfirmDialog.getByRole('button', {
    name: 'Confirm and Archive',
  });

  await expect(cancelButton).toBeEnabled();
  await expect(confirmArchiveButton).toBeVisible();
  await expect(confirmArchiveButton).toBeDisabled();

  const irreversibleCheckbox = finalConfirmDialog.getByRole('checkbox', {
    name: 'I understand this action cannot be undone',
  });
  await expect(irreversibleCheckbox).not.toBeChecked();
  await irreversibleCheckbox.check();
  await expect(irreversibleCheckbox).toBeChecked();
  await expect(confirmArchiveButton).toBeEnabled();
  await confirmArchiveButton.click();

  const notification = page.locator('app-custom-snack-bar');
  await expect(notification).toContainText(
    /file mapping submitted and upload box archived successfully/i,
  );

  await expect(uploadBoxInfoCard).toContainText('State:');
  await expect(uploadBoxInfoCard).toContainText('Archived');

  const archivedStorageTable = page
    .locator('mat-card')
    .filter({ has: page.getByRole('heading', { level: 2, name: 'Storage & Files' }) })
    .locator('table');

  await expect(
    archivedStorageTable.getByRole('columnheader', { name: 'Accession' }),
  ).toBeVisible();

  const methArchivedRow = archivedStorageTable
    .locator('tr')
    .filter({ hasText: 'methylation_sample_001.meth' })
    .first();
  await expect(methArchivedRow).toContainText('GHGAF99999999999010');
});
