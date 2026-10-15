import assert from 'node:assert/strict'
import { readArticle, filterTopics } from '../src/features/help/help.js'

const article = readArticle('clock', '# Database clock\n\n`CURRENT_TIMESTAMP` and `Site.get_site_data()`', 'clock.en.md')
for (const query of ['CURRENT_TIMESTAMP', 'current timestamp', '  Site.get_site_data()  ', 'Site.get site data', 'CURRENT\n  TIMESTAMP']) {
  assert.deepEqual(filterTopics([article], query), [article], query)
}
assert.deepEqual(filterTopics([article], 'missing_method'), [])
console.log('Help search: code names and plain-text queries normalize equally.')
