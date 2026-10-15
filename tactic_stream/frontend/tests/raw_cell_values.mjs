import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { cellText, cellValue } from '../src/features/administration/rawCellValues.js'

const vectors = JSON.parse(await readFile(new URL('../../tests/fixtures/raw_cell_values.json', import.meta.url), 'utf8'))
for (const entry of vectors.valid) assert.deepEqual(cellValue(entry.text, entry.type, entry.mode), entry.value, JSON.stringify(entry))
for (const entry of vectors.invalid) assert.throws(() => cellValue(entry.text, entry.type, entry.mode), JSON.stringify(entry))
for (const text of ['plain', 'NULL', '"quoted"', 'line one\nline two', '42', '']) assert.equal(cellText(text), text)
assert.equal(cellText(null), '')
assert.equal(cellText({flag:true}), '{"flag":true}')
console.log(`Plain cell conversion: ${vectors.valid.length} valid and ${vectors.invalid.length} invalid shared cases passed.`)
