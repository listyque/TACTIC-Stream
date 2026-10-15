import assert from 'node:assert/strict'
import { escapeHtml, linkifyPlainText, activateRichLink } from '../src/controls/richText.js'
import { addressProject, projectPath, browserLink, linkProject, searchLink, savedSearchLink, workspaceAddress } from '../src/features/workspace/links.js'

const key = 'skey://cg/assets?project=cg_test&code=ROBOT'
const html = linkifyPlainText(`<img src=x onerror=alert(1)>\n(${key}). https://example.org/?a=1&b=2 javascript://danger`, browserLink)
assert(!html.includes('<img'))
assert(html.includes('&lt;img'))
assert(html.includes('<br>'))
assert(html.includes('data-rich-link="' + escapeHtml(key) + '"'))
assert(html.includes('href="' + escapeHtml(browserLink(key)) + '"'))
assert(html.includes('target="_blank" rel="noopener noreferrer"'))
assert(html.includes('</a>).'))
assert.equal((html.match(/<a /g) || []).length, 2)
assert.equal(linkProject(key, 'admin'), 'cg_test')
assert.equal(linkProject('SKEY://cg/assets?project_code=cg_test&id=5', 'admin'), 'cg_test')
assert.equal(linkProject('skey://cg/assets?code=ROBOT', 'admin'), 'admin')
assert.throws(() => linkProject('javascript://danger', 'admin'))
assert.throws(() => linkProject(key + '\n', 'admin'))
assert.equal(searchLink('cg/assets?project=cg_test&id=1'), 'skey://cg/assets?project=cg_test&id=1')
assert.equal(searchLink('Ordinary words'), '')
const saved = savedSearchLink('cg_test', 'cg/assets', 'link_search:robot:cg/assets')
assert.equal(new URL('http://local' + browserLink(saved)).searchParams.get('link'), saved)
assert.equal(addressProject(new URL('http://local' + workspaceAddress('cg_test', 'cg/assets', 'table'))), 'cg_test')
assert.equal(new URL('http://local' + workspaceAddress('cg_test', 'cg/assets', 'table')).pathname, '/projects/cg_test/')
assert.equal(addressProject(new URL('http://local/admin/?project=legacy')), '')
assert.equal(addressProject(new URL('http://local/projects/current/?project=legacy')), 'current')
assert.equal(addressProject(new URL('http://local/projects/%ZZ/')), '')
assert.equal(addressProject(new URL('http://local' + projectPath('тест & #?'))), 'тест & #?')
assert.equal(new URL('http://local' + browserLink('skey://sthpw/login?code=admin')).pathname, '/')
assert.equal(new URL('http://local' + browserLink('skey://cg/assets?code=A', 'cg_test')).pathname, '/projects/cg_test/')
assert.equal(workspaceAddress('cg_test', 'cg/scenes', 'table'), '/projects/cg_test/?search_type=cg%2Fscenes&view=table', 'Shared addresses contain only the project, Search Type and view')
assert.equal(workspaceAddress('cg_test', 'cg/assets', 'table', key), browserLink(key), 'sKey remains the shared object address')
let opened = '', prevented = false
const event = { target: { closest: () => ({ dataset: { richLink: key } }) }, button: 0, preventDefault: () => { prevented = true } }
assert(activateRichLink(event, value => { opened = value })); assert.equal(opened, key); assert(prevented)
opened = ''; assert.equal(activateRichLink({ ...event, ctrlKey: true }, value => { opened = value }), false); assert.equal(opened, '')
console.log('Safe native linkification, browser URLs, project context and modified-click behavior PASS')
