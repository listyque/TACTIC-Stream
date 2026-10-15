import assert from 'node:assert/strict'
import { activate, captureLayout, decodeLayout, defaults, ids, place, projectTree, readDocks, readTree, remove, stack } from '../src/features/workspace/docks.js'

let tree = place(stack('results'), 'tasks', 'right')
assert.equal(tree.ratio, .66)
assert.deepEqual(ids(tree), ['results', 'tasks'])
assert.deepEqual(projectTree(tree, ['results'], 1000, 900).stacks[0].rect, [0, 0, 1, 1], 'Hidden panels do not reserve space')
tree = place(tree, 'commit_queue', 'center', 'tasks')
assert.equal(projectTree(tree, ids(tree), 1000, 900).stacks[1].active, 'commit_queue')
tree = activate(tree, 'tasks')
assert.equal(projectTree(tree, ids(tree), 1000, 900).stacks[1].active, 'tasks')
tree = place(tree, 'commit_queue', 'bottom', 'results')
assert.equal(tree.first.orientation, 'vertical')
assert.equal(tree.first.ratio, .5)
const swapped = place(tree, 'results', 'swap', 'tasks')
assert.deepEqual(ids(swapped), ['tasks', 'commit_queue', 'results'])
assert.deepEqual(ids(remove(swapped, 'commit_queue')), ['tasks', 'results'])
assert.equal(place(stack('results'), 'tasks', 'swap', 'results').orientation, 'horizontal', 'Floating swap falls back to a right split')
assert.deepEqual(readTree({ type: 'stack', panels: ['evil', 'tasks', 'tasks', 'results'], active: 'evil' }),
  { type: 'stack', panels: ['tasks', 'results'], active: 'tasks' })
assert.equal(readTree({ type: 'split', orientation: 'invalid' }), null)
assert.deepEqual(readTree(JSON.parse(JSON.stringify(tree))), tree)
const projected = projectTree(tree, ids(tree), 1600, 1000)
assert.equal(projected.stacks.length, 3)
assert.equal(projected.dividers.length, 2)
assert.equal(projected.stacks.reduce((sum, item) => sum + item.rect[2] * item.rect[3], 0), 1)
globalThis.localStorage = { getItem: () => JSON.stringify({ panels: { tasks: { visible: true, floating: true, z: 9, rect: [.1, .2, .4, .5] } } }) }
const restored = readDocks('admin')
assert.equal(restored.panels.tasks.z, 9, 'Floating overlap order restores with geometry')
assert.deepEqual(restored.panels.tasks.rect, [.1, .2, .4, .5])
delete globalThis.localStorage
const document = captureLayout(defaults())
assert.deepEqual(decodeLayout(document), defaults())
const unavailable = { ...document, panels: [...document.panels, { panel_id: 'unknown_panel', visible: true }] }
assert.throws(() => decodeLayout(unavailable), /not been migrated/)
unavailable.panels.at(-1).visible = false
assert.deepEqual(decodeLayout(unavailable), defaults(), 'Hidden native docks do not prevent using a layout')
const expanded = defaults()
expanded.panels.description.visible = true
expanded.layout = place(expanded.layout, 'description', 'right')
expanded.maximized = 'description'; expanded.compactActive = 'description'
const browserLayout = { ...captureLayout(expanded), presentation: { maximized:'description', compactActive:'description' } }
assert.deepEqual(decodeLayout(browserLayout), expanded, 'Per-tab presentation keeps maximize and compact selection')
assert.equal(decodeLayout({ ...browserLayout, presentation:{ maximized:'unknown', compactActive:'tasks' } }).maximized, '')
assert.equal(decodeLayout({ ...browserLayout, presentation:{ compactActive:'tasks' } }).compactActive, 'tasks', 'Phone panel choice survives without enabling a desktop dock')
globalThis.localStorage = { getItem: () => JSON.stringify(expanded) }
assert.deepEqual(readDocks('alice'), expanded, 'Account fallback keeps the same presentation')
expanded.layout = null
assert.equal(captureLayout(expanded).layout.type, 'stack', 'An entirely floating workspace still has a native tree')
delete globalThis.localStorage
console.log('Dock tree: placement, tab stacks, swap, visibility, geometry and untrusted saved state OK')

const inspector = defaults()
inspector.panels.notes.visible = true
inspector.layout = place(inspector.layout, 'notes', 'right')
assert.deepEqual(decodeLayout(captureLayout(inspector)), inspector, 'Native notes dock is supported by saved layouts')
