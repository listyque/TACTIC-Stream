import assert from 'node:assert/strict';

export async function chooseStatus(picker, value) {
  if ((await picker.getAttribute('open')) === null)
    await picker.locator(':scope > summary').click();
  await picker.locator('.status-select-option').first().waitFor();
  for (const option of await picker.getByRole('menuitemradio').all()) {
    if ((await option.getAttribute('data-value')) === value) {
      await option.click();
      return;
    }
  }
  assert.fail('Status choice not found: ' + value);
}

export const statusValues = (picker) =>
  picker
    .locator('.status-select-option:not(:disabled)')
    .evaluateAll((options) => options.map((option) => option.dataset.value));
