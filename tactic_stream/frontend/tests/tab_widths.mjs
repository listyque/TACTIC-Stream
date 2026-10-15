import assert from 'node:assert/strict'
import fs from 'node:fs'
import { displacedTabOffset, fitTabWidths } from '../src/controls/tabWidths.js'

const source = fs.readFileSync('D:/code/th_codex/thlib/ui/qml/SearchWorkspaceView.qml', 'utf8')
const start = source.indexOf('readonly property real fittedTabWidth: {')
assert(start >= 0)
const end = source.indexOf('property real displacedX:', start)
const block = source.slice(start, end)
const nativeWidth = new Function('searchTabsView', 'current', 'naturalTabWidth', 'minimumTabWidth', block.slice(block.indexOf('{') + 1, block.lastIndexOf('}')))
let comparisons = 0
for (const natural of [[96], [160, 360, 120], [96, 96, 400], [180, 84, 110, 160], [84, 84, 84]]) {
  for (const minimum of [84, 96]) {
    if (natural.some(width => width < minimum)) continue
    for (const available of [100, 180, 260, 480, 700, 1000]) for (let current = 0; current < natural.length; current++) {
      const fitted = fitTabWidths(natural, current, available, minimum)
      const native = natural.map((width, index) => nativeWidth({ width: available, naturalContentWidth: natural.reduce((sum, value) => sum + value, 0),
        count: natural.length, activeNaturalWidth: natural[current] }, index === current, width, minimum))
      assert.deepEqual(fitted, native)
      assert.equal(fitted[current], natural[current])
      assert(fitted.every(width => Number.isFinite(width) && width >= minimum))
      comparisons++
    }
  }
}
assert.deepEqual(fitTabWidths([], -1, 300, 96), [])
assert.deepEqual(fitTabWidths([160, 200], -1, 192, 96), [96, 96])
console.log(`PASS: ${comparisons} comparisons with unchanged QML fittedTabWidth, active width, minima and empty state`)
const displacement = source.slice(end, source.indexOf('width: fittedTabWidth', end))
const nativeOffset = new Function('searchTabsView', 'index', displacement.slice(displacement.indexOf('{') + 1, displacement.lastIndexOf('}')))
let offsets = 0
for (let from = -1; from < 5; from++) for (let to = -1; to < 5; to++) {
  for (let index = 0; index < 5; index++) for (const width of [84, 96, 164.5, 360]) {
    assert.equal(displacedTabOffset(index, from, to, width), nativeOffset({ dragSourceIndex: from, dragTargetIndex: to, draggedTabWidth: width }, index))
    offsets++
  }
}
console.log(`PASS: ${offsets} displacement comparisons with unchanged QML displacedX`)
const railSource = fs.readFileSync('D:/code/th_codex/thlib/ui/qml/SectionTabRail.qml', 'utf8')
const railBlock = railSource.slice(railSource.indexOf('property real displacedY:'), railSource.indexOf('width: revealed ? expandedWidth'))
const nativeRailOffset = new Function('rail', 'index', 'height', railBlock.slice(railBlock.indexOf('{') + 1, railBlock.lastIndexOf('}')))
for (let from = -1; from < 5; from++) for (let to = -1; to < 5; to++) for (let index = 0; index < 5; index++) {
  assert.equal(displacedTabOffset(index, from, to, 45), nativeRailOffset({ dragSourceIndex: from, dragTargetIndex: to, spacing: 3 }, index, 42))
}
console.log('PASS: 180 comparisons with unchanged SectionTabRail displacedY')
