// Exercise the public chooser instead of changing Vue state from a test.
export async function selectProject(page, code) {
  if (code === '__create_project__') {
    await page.locator('.settings-menu > summary').click()
    await page.locator('.settings-menu').getByRole('button', { name: 'Create project', exact: true }).click()
    return
  }
  await page.locator('.project-picker').click()
  const chooser = page.locator('#project-chooser')
  const target = chooser.locator(`.project-card[data-project="${code}"]`)
  if (!await target.count()) for (const name of ['Retired', 'Templates', 'Built-in']) await chooser.getByRole('checkbox', { name, exact: true }).check()
  await target.click()
  await chooser.waitFor({ state: 'hidden' })
}

export async function openViewActions(page) {
  const actions = page.locator('summary[aria-label="View actions"]')
  if (!await actions.isVisible()) {
    await page.getByLabel('Workspace panels', { exact:true }).click()
    await page.locator('.dock-menu summary[aria-label="Tools"]').click()
  }
  await actions.click()
}
