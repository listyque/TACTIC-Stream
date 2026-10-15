import assert from 'node:assert/strict'
import { editCommand, findMatches, documentSymbols, completions } from '../src/controls/codeEditing.js'
import { pythonTokens, javascriptTokens } from '../src/controls/pythonSyntax.js'
assert.deepEqual(editCommand('toggle_comment', '  x = 1\n  y = 2', 0, 17), { text: '  # x = 1\n  # y = 2', start: 0, end: 19 })
assert.equal(editCommand('toggle_comment', '  // x = 1', 0, 10, 'javascript').text, '  x = 1')
assert.equal(editCommand('unindent', '\tfoo\n  bar', 0, 10).text, 'foo\nbar')
assert.deepEqual(editCommand('duplicate', 'foo\nbar', 1, 1), { text: 'foo\nfoo\nbar', start: 4, end: 7 })
assert.equal(editCommand('delete_line', 'foo\nbar', 5, 5).text, 'foo')
assert.deepEqual(findMatches('foo Foo food', 'foo', { wholeWord: true }), [{ start: 0, end: 3 }, { start: 4, end: 7 }])
assert.deepEqual(findMatches('a.b axb', 'a.b'), [{ start: 0, end: 3 }])
assert.deepEqual(findMatches('abc', '[', { regex: true }), [])
assert.equal(documentSymbols('def hello():\n    pass\nclass World:\n    pass', 'python')[1].name, 'World')
assert.equal(documentSymbols('export async function hello() {}', 'javascript')[0].name, 'hello')
assert(completions('const custom = 1;\ncus', 21, 'javascript').some(row => row.name === 'custom'))
assert.deepEqual(completions('server.que', 10, 'python', ['query', 'insert']), [{ name: 'query', start: 7, end: 10 }])
for (const [source, tokenize] of [['print("<script>") # comment\n', pythonTokens], ['const x = "<script>"; // comment\n', javascriptTokens]]) {
  const tokens = tokenize(source); assert.equal(tokens.map(row => row.text).join(''), source); assert(tokens.some(row => row.role === 'string')); assert(tokens.some(row => row.role === 'comment'))
}
console.log('PASS code editing, search boundaries, symbols, completion and Python/JS tokens')
