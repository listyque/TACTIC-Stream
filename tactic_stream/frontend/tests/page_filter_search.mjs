import assert from 'node:assert/strict';
import * as Filters from '../../src/tactic_stream/shared_ui/features/table/page.filters.mjs';
import { highlight } from '../../src/tactic_stream/shared_ui/controls/forms/search.mjs';
const definitions = [
  {
    name: 'status',
    title: 'Status',
    dataType: 'text',
    relation: '=',
    value: '',
    enabled: false
  },
  {
    name: 'amount',
    title: 'Amount',
    dataType: 'numeric',
    relation: '>=',
    value: 0,
    enabled: false
  }
];
let draft = Filters.initial(definitions);
assert.deepEqual(Filters.query(definitions, 'sTaTuS: In progress'), {
  field: 'status',
  text: 'In progress'
});
assert.throws(() => Filters.query(definitions, 'password: x'));
const fields = Filters.suggestions(definitions, 'sta');
assert.equal(fields[0].name, 'status');
assert.ok(fields[0].field);
let result = Filters.choose(definitions, draft, fields[0]);
assert.equal(result.apply, false);
assert.equal(result.text, 'Status: ');
const choices = Filters.suggestions(definitions, 'progress', [
  { name: 'status', value: 'In Progress' }
]);
result = Filters.choose(definitions, draft, choices[0]);
draft = result.draft;
assert.equal(result.apply, true);
assert.deepEqual(Filters.values(definitions, draft).status, {
  enabled: true,
  value: 'In Progress'
});
result = Filters.submit(definitions, draft, 'Amount: 0', []);
assert.equal(result.draft.amount.value, 0);
assert.throws(() => Filters.submit(definitions, draft, 'Amount: wrong', []));
assert.equal(
  Filters.describe(definitions, draft, 320, 'en').nodes[0].view,
  'pageFilterSearch'
);
assert.equal(
  Filters.describe(definitions, draft, 320, 'en').nodes.some(
    (node) => node.kind === 'CheckBox'
  ),
  false
);
assert.equal(
  highlight('<img onerror="bad">&', 'IMG'),
  '&lt;<u>img</u> onerror=&quot;bad&quot;&gt;&amp;'
);
assert.equal(highlight('In Progress', 'pro'), 'In <u>Pro</u>gress');
console.log(
  'Page search: configured fields, typed zero, immutable conditions, chips and escaped highlighting pass'
);
