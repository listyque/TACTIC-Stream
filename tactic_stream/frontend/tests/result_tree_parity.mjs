import assert from 'node:assert/strict'
import { chromium } from 'playwright'
import { selectProject } from './project_selection.mjs'

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1452, height: 900 } })
const project = process.env.STREAM_CHECK_PROJECT || 'cg_test'
const errors = []
page.on('pageerror', error => errors.push(error.message))
try {
  await page.addInitScript(project => {
    localStorage.setItem('tactic_stream.appearance', JSON.stringify({ mode: 'dark', language: 'en' }))
    localStorage.setItem('tactic_stream.workspace.admin', JSON.stringify({ [project]: {
      current: 'episode', sections: [{ id: 'episode', type: 'cg/scenes', title: 'Episode', view: 'table', configuredView: false,
        current: 'episode-tab', tabs: [{ id: 'episode-tab', title: 'Episode', state: { type: 'cg/scenes', view: 'table', configuredView: false } }] }],
    } }))
  }, project)
  await page.goto(process.argv[2] + '/projects/admin/?search_type=sthpw/project&view=table')
  await page.getByLabel('Login', { exact: true }).fill(process.env.STREAM_CHECK_LOGIN || 'admin')
  await page.getByLabel('Password', { exact: true }).fill(process.env.STREAM_CHECK_PASSWORD)
  await page.getByRole('button', { name: 'Sign in', exact: true }).click()
  await selectProject(page, project)
  await page.getByLabel('Change search results view', { exact: true }).click()
  await page.getByRole('menuitemradio', { name: 'Continuous tree', exact: true }).click()
  const episode = page.locator('.workspace-browser article[data-result-key*="code=DEMO_EP01"]').first()
  await episode.getByRole('button', { name: 'Expand item', exact: true }).click()
  const branches = page.locator('.workspace-browser .result-item-branch')
  await branches.filter({ hasText: 'Assets' }).waitFor()
  await page.mouse.move(0, 0)
  await page.waitForTimeout(150)
  const geometry = await page.locator('.workspace-browser .result-presentation:visible').evaluate(root => {
    const article = root.querySelector('article')
    const relation = root.querySelector('.result-item-relation')
    const process = root.querySelector('.result-item-process')
    const style = element => {
      const css = getComputedStyle(element), box = element.getBoundingClientRect()
      return { height: box.height, width: box.width, left: box.left, top: box.top,
        background: css.backgroundColor, fontSize: css.fontSize, fontWeight: css.fontWeight, fontFamily: css.fontFamily, color: css.color }
    }
    return { object: style(article), preview: style(article.querySelector('.image-picker-preview')),
      title: style(article.querySelector('strong')), subtitle: style(article.querySelector('.result-description')),
      relation: style(relation), process: style(process), branchTitle: style(process.querySelector('strong')),
      surface: style(process.querySelector('.result-surface')), background: style(root),
      glyph: style(relation.querySelector('.result-branch-icon .icon-glyph')),
      titles: [...root.querySelectorAll('.result-item-branch strong')].map(element => element.textContent),
      initials: article.querySelector('.image-picker-preview').textContent.trim(),
    }
  })
  const cdp = await page.context().newCDPSession(page)
  await cdp.send('DOM.enable'); await cdp.send('CSS.enable')
  const { root } = await cdp.send('DOM.getDocument')
  const { nodeId } = await cdp.send('DOM.querySelector', { nodeId: root.nodeId, selector: '.workspace-browser .result-description' })
  console.log('Rendered font:', JSON.stringify(await cdp.send('CSS.getPlatformFontsForNode', { nodeId })))
  console.log('Measured QML geometry:', JSON.stringify(geometry))
  assert.equal(geometry.object.height, 100)
  assert.equal(geometry.preview.width, 68)
  assert.equal(geometry.title.fontSize, '15px')
  assert.equal(geometry.subtitle.fontWeight, '400')
  assert.equal(geometry.process.height, 32)
  assert.equal(geometry.relation.height, 38)
  assert.equal(geometry.branchTitle.fontWeight, '600')
  assert.equal(geometry.glyph.fontSize, '14px')
  assert.notEqual(geometry.surface.background, geometry.background.background)
  assert.equal(geometry.initials, 'EA')
  assert.deepEqual(geometry.titles.slice(0, 2), ['Shot', 'Assets'])
  await episode.getByRole('button', { name: /assets: 0 \/ 3/ }).waitFor()
  await page.screenshot({ path: '../.screenshots/results-episode-parity.png', animations: 'disabled' })
  await episode.getByRole('button', { name: 'Collapse item', exact: true }).click()
  await branches.first().waitFor({ state: 'detached' })
  await episode.getByRole('button', { name: 'Expand item', exact: true }).click()
  await branches.first().waitFor()
  await branches.filter({ hasText: 'Assets' }).getByRole('button', { name: 'Create related object', exact: true }).click()
  const form = page.getByRole('dialog', { name: 'Record form', exact: true })
  await form.getByLabel('Name', { exact: true }).waitFor()
  await form.getByRole('button', { name: 'Close', exact: true }).click()
  assert.deepEqual(errors, [])
  console.log('PASS: Episode tree geometry, palette, glyphs, relation order/counts, disclosure and insert form opening (Preview remains unsupported)')
} catch (error) {
  await page.screenshot({ path: '../.screenshots/results-episode-failure.png', animations: 'disabled' })
  throw error
} finally { await browser.close() }
