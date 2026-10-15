import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

// Load the resolver and real charmaps without requiring a browser or Vite.
const source = readFileSync(new URL('../src/icons.js', import.meta.url), 'utf8')
const code = source.replace(/^import (\w+) from '([^']+)'/gm, (_, name, path) =>
  `const ${name} = ${readFileSync(new URL('../src/' + path, import.meta.url), 'utf8')}`)
const { resolveIcon, iconMaps } = await import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'))
for (const [family, map] of Object.entries(iconMaps)) {
  const name = Object.keys(map)[0], value = map[name]
  assert.deepEqual(resolveIcon(family + ':' + name, 'automatic'), [family, String.fromCodePoint(typeof value === 'number' ? value : parseInt(value, 16))])
}
assert.deepEqual(resolveIcon('FAS_PLAY', 'material-design'), resolveIcon('fontawesome-solid:play', 'material-design'))
assert.deepEqual(resolveIcon('MDI_PLAY', 'fontawesome-solid'), resolveIcon('material-design:play', 'fontawesome-solid'))
assert.deepEqual(resolveIcon('play-arrow', 'material-design'), resolveIcon('material-design:play', 'material-design'))
assert.equal(resolveIcon('unknown:play', 'fontawesome-solid'), undefined)
assert.equal(resolveIcon('fontawesome-solid:missing-icon', 'material-design'), undefined)
assert.equal(resolveIcon('', 'material-design'), undefined)
for (const pack of Object.keys(iconMaps)) for (const name of ['schedule','history','person','process','status','sobject','schema','workspaces','priority-high','milestone','admin-panel-settings','ungroup-items']) assert(resolveIcon(name,pack),pack+':'+name)
for (const pack of Object.keys(iconMaps)) for (const name of ['dns', 'desktop', 'delete-sweep', 'priority-high', 'warning', 'info', 'notifications', 'activity-feed', 'dynamic-feed', 'sync', 'check-circle', 'task', 'notes', 'snapshot', 'select-all', 'inventory-2', 'system-activity', 'schedule', 'groups', 'open-in-full', 'window-restore']) assert(resolveIcon(name, pack), pack + ':' + name)
console.log('PASS all five native set:name icon catalogs and legacy aliases')
for (const pack of Object.keys(iconMaps)) {
  const name = pack.startsWith('fluent-') ? 'text-description' : pack === 'material-design' ? 'text-box' : 'file-alt'
  const family = iconMaps[pack][name] ? pack : 'fontawesome-solid'
  assert.deepEqual(resolveIcon('description', pack), resolveIcon(family + ':' + name, pack))
}
for (const pack of Object.keys(iconMaps)) assert(resolveIcon('tab', pack), pack + ':tab')
for (const pack of Object.keys(iconMaps)) {
  const family = pack === 'fontawesome-outline' ? 'fontawesome-solid' : pack
  const name = pack.startsWith('fluent-') ? 'cloud-arrow-up' : pack === 'material-design' ? 'cloud-upload' : 'cloud-upload-alt'
  assert.deepEqual(resolveIcon('commit-queue', pack), resolveIcon(family + ':' + name, pack))
}

for (const pack of Object.keys(iconMaps)) for (const name of ['book-open', 'file', 'person-add']) assert(resolveIcon(name, pack), pack + ':' + name)
