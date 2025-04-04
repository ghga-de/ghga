/**
 * Playwright test for work-package page.
 * @copyright The GHGA Authors
 * @license Apache-2.0
 */

import { expect, test } from './fixtures';

test('allow the creation of a download token', async ({ loggedInPage }) => {
  const page = loggedInPage;

  const accountMenu = page.getByRole('button', { name: 'Account' });
  await accountMenu.click();
  const accountItem = page.getByRole('menuitem', { name: 'Your GHGA account page' });
  await accountItem.click();
  const setupButton = page.getByRole('button', { name: 'Set up a download token' });
  await setupButton.click();

  await expect(page).toHaveTitle('Download or Upload Datasets | GHGA Data Portal');
  await expect(page).toHaveURL('/work-package');

  const main = page.locator('main');
  const heading = main.getByRole('heading', { level: 1 });
  await expect(heading).toHaveText('Download or upload datasets');

  await expect(main).toContainText('please select one of your available dataset');
  const datasetSelector = main.getByRole('combobox', { name: 'Available datasets' });
  await datasetSelector.click();
  const datasetOption = page.getByRole('option', {
    name: 'GHGAD588887988: Some dataset to download',
  });
  await datasetOption.click();

  await expect(main).toContainText('This is a very interesting dataset');
  await expect(main).toContainText('This dataset has been selected for download.');

  const keyBox = main.getByRole('textbox', { name: 'Your public Crypt4GH key' });
  await keyBox.fill('something');
  await expect(main).toContainText(
    'This does not seem to be a Base64 encoded Crypt4GH key.',
  );
  await keyBox.fill('MTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI');
  await expect(main).not.toContainText('This does not seem to be');

  const generateButton = main.getByRole('button', {
    name: 'Generate an access token for download',
  });
  generateButton.click();

  await expect(main).toContainText('Your download token has been created.');
  await expect(main).toContainText(
    'Please use the following token to download the selected dataset:',
  );
  const copyButton = main.getByRole('button', {
    name: 'Copy token to clipboard',
  });
  await copyButton.click();

  await expect(
    page.getByText('The token has been copied to the clipboard.'),
  ).toBeVisible();
});
