export async function closeInspector(page) {
  const button = page.locator('[data-dock="notes"]').getByRole('button', { name: /^(Close panel: Task Inspector|Back)$/ })
  if (page.viewportSize().width <= 700) await button.tap()
  else await button.click()
}
