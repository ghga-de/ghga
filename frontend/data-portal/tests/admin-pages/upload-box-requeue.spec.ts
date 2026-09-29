/**
 * Playwright tests for retrying the re-encryption of failed file uploads.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { Page } from '@playwright/test';
import { expectTitle } from '../utils/expect-title';
import { expect, test } from './admin-fixtures';

test.use({
  adminMenuItemName: 'Upload Box Manager',
  adminMenuItemUrl: '/upload-box-manager',
});

/** John's open box, holding one file whose re-encryption failed */
const OPEN_BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68001';
/** Jim's locked box, holding one file whose re-encryption failed */
const LOCKED_BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68006';
/** Jane's locked box, whose only failed file never reached re-encryption */
const SETTLED_LOCKED_BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68002';
/** Joan's archived box */
const ARCHIVED_BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68003';
/** John's third box, open but with no file waiting for a retry */
const SETTLED_BOX_ID = '0a36607a-b53f-49ed-bf3e-a5f2dbc68005';

const OPEN_BOX_FAILED_FILE = 'sample_rna_002_R2.fastq.gz';
const OPEN_BOX_DONE_FILE = 'sample_rna_001_R1.fastq.gz';
const LOCKED_BOX_FAILED_FILE = 'retry_sample_002.fastq.gz';

/**
 * Open the detail page of an upload box directly.
 * @param page - the Playwright page
 * @param boxId - the ID of the upload box to open
 */
async function goToBox(page: Page, boxId: string) {
  await page.goto(`/upload-box-manager/${boxId}`);
  await expectTitle(page, 'Upload Box Details');
}

/**
 * The row of the file list showing a single file.
 * @param page - the Playwright page
 * @param alias - the alias (file name) of the file
 * @returns the locator of the table row
 */
function fileRow(page: Page, alias: string) {
  return page
    .locator('app-upload-box-files-table table tbody tr')
    .filter({ hasText: alias });
}

/**
 * The button retrying the re-encryption of a single file.
 * @param page - the Playwright page
 * @param alias - the alias (file name) of the file
 * @returns the locator of the retry button
 */
function retryButton(page: Page, alias: string) {
  return fileRow(page, alias).getByRole('button', {
    name: `Retry re-encryption of ${alias}`,
  });
}

/** All per-file retry buttons of the currently shown page of the file list */
const anyRetryButton = (page: Page) =>
  page.getByRole('button', { name: /^Retry re-encryption of / });

/** The button retrying every failed re-encryption of the box at once */
const retryAllButton = (page: Page) =>
  page.getByRole('button', { name: 'Retry failed re-encryptions' });

/** The snack bar reporting the outcome of an action */
const notification = (page: Page) => page.locator('app-custom-snack-bar');

/**
 * Which retry affordances each box state offers. One test rather than one per
 * box: none of these steps interacts with the backend, and every test of this
 * suite pays for its own login.
 */
test('offers the retry only where a file is waiting for one', async ({
  adminPage: page,
}) => {
  // An open box holding a failed file offers both retries.
  await goToBox(page, OPEN_BOX_ID);
  await expect(fileRow(page, OPEN_BOX_FAILED_FILE)).toContainText(
    're-encryption failed',
  );
  await expect(retryButton(page, OPEN_BOX_FAILED_FILE)).toBeVisible();
  // A file that has been re-encrypted has nothing to retry.
  await expect(fileRow(page, OPEN_BOX_DONE_FILE)).toContainText('re-encrypted');
  await expect(retryButton(page, OPEN_BOX_DONE_FILE)).toHaveCount(0);
  // The whole-box retry is only offered once the complete file list has shown
  // that some file actually failed.
  await expect(retryAllButton(page)).toBeVisible();

  // A locked box offers the retry just the same, but no deletion: files can
  // only be deleted while the box is still open for uploads.
  await goToBox(page, LOCKED_BOX_ID);
  await expect(fileRow(page, LOCKED_BOX_FAILED_FILE)).toContainText(
    're-encryption failed',
  );
  await expect(retryButton(page, LOCKED_BOX_FAILED_FILE)).toBeVisible();
  await expect(retryAllButton(page)).toBeVisible();
  await expect(page.getByRole('button', { name: /^Delete file / })).toHaveCount(0);

  // A locked box whose only failed file never reached re-encryption offers
  // nothing: 'failed' is not 'failed_interrogation' and cannot be requeued.
  await goToBox(page, SETTLED_LOCKED_BOX_ID);
  await expect(fileRow(page, 'sample_001_R1.fastq')).toBeVisible();
  await expect(anyRetryButton(page)).toHaveCount(0);
  await expect(retryAllButton(page)).toHaveCount(0);

  // Neither does an open box whose files are all settled.
  await goToBox(page, SETTLED_BOX_ID);
  await expect(fileRow(page, 'sample_image_001.tiff')).toBeVisible();
  await expect(anyRetryButton(page)).toHaveCount(0);
  await expect(retryAllButton(page)).toHaveCount(0);

  // Archived boxes report the accession instead of the upload status, and
  // their files can never be requeued.
  await goToBox(page, ARCHIVED_BOX_ID);
  const filesTable = page.locator('app-upload-box-files-table table');
  await expect(
    filesTable.getByRole('columnheader', { name: 'Accession' }),
  ).toBeVisible();
  await expect(anyRetryButton(page)).toHaveCount(0);
  await expect(retryAllButton(page)).toHaveCount(0);
});

/**
 * The two requeue tests below assert what the page shows *after* the mutation,
 * which the mocking philosophy otherwise rules out for this layer. It holds here
 * because the change is client-side: `UploadBoxService` moves the requeued files
 * back to the inbox state in its own signals rather than fetching the list again,
 * so the assertion covers real application code and not a mock pretending to be a
 * backend. Anything whose outcome depends on the backend still belongs in the
 * test bed.
 */
test('requeues a single file and shows it back in re-encryption', async ({
  adminPage: page,
}) => {
  await goToBox(page, OPEN_BOX_ID);
  // Wait for the complete file list, so that the button count asserted at the
  // end reflects the requeue rather than a list that has not arrived yet.
  await expect(retryAllButton(page)).toBeVisible();

  await retryButton(page, OPEN_BOX_FAILED_FILE).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Retry re-encryption?');
  await expect(dialog).toContainText(OPEN_BOX_FAILED_FILE);

  const requeueRequest = page.waitForRequest(
    (request) =>
      request.method() === 'POST' &&
      request.url().includes(`/api/rs/rpc/upload-boxes/${OPEN_BOX_ID}/uploads/`) &&
      request.url().endsWith('/requeue'),
  );
  await dialog.getByRole('button', { name: 'Retry', exact: true }).click();
  await requeueRequest;

  await expect(notification(page)).toContainText(/queued for re-encryption/i);

  // The file is back in re-encryption, so neither retry is offered any more.
  await expect(fileRow(page, OPEN_BOX_FAILED_FILE)).toContainText('re-encrypting');
  await expect(anyRetryButton(page)).toHaveCount(0);
  await expect(retryAllButton(page)).toHaveCount(0);
});

test('requeues every failed file of a box at once', async ({ adminPage: page }) => {
  await goToBox(page, OPEN_BOX_ID);
  await expect(retryAllButton(page)).toBeVisible();

  await retryAllButton(page).click();

  const dialog = page.getByRole('dialog');
  await expect(dialog).toContainText('Retry all failed re-encryptions?');

  const requeueRequest = page.waitForRequest(
    (request) =>
      request.method() === 'POST' &&
      request.url().endsWith(`/api/rs/rpc/upload-boxes/${OPEN_BOX_ID}/requeue`),
  );
  await dialog.getByRole('button', { name: 'Retry all' }).click();
  await requeueRequest;

  await expect(notification(page)).toContainText('1 file queued for re-encryption.');

  await expect(fileRow(page, OPEN_BOX_FAILED_FILE)).toContainText('re-encrypting');
  await expect(anyRetryButton(page)).toHaveCount(0);
  await expect(retryAllButton(page)).toHaveCount(0);
});
