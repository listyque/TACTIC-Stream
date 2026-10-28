import assert from 'node:assert/strict';
import {
  describe,
  edit
} from '../../src/tactic_stream/shared_ui/features/administration/layouts/layout.document.mjs';

const navigation = {
  'demo/project': ['demo/chat'],
  'demo/chat': ['sthpw/task'],
  'sthpw/task': []
};
const view = {
  type: 1,
  name: 'flow',
  attributes: [
    ['layout', 'sobject-layout'],
    ['collection', 'tree'],
    ['navigation', JSON.stringify(navigation)]
  ],
  children: [
    { type: 1, name: 'element', attributes: [['name', 'title']], children: [] }
  ]
};
const tree = { type: 1, name: 'config', attributes: [], children: [view] };
assert.deepEqual(describe(tree, 'flow').navigation, navigation);
edit(tree, 'flow', 'title', 'title', 'Project title');
assert.deepEqual(
  describe(tree, 'flow').navigation,
  navigation,
  'Editing a card must retain its navigation projection'
);
view.attributes = view.attributes.filter(([key]) => key !== 'navigation');
assert.equal(describe(tree, 'flow').navigation, undefined);
view.attributes.push(['navigation', '{']);
assert.throws(() => describe(tree, 'flow'));
console.log(
  'Tree navigation survives item editor changes; ordinary layouts remain unconfigured'
);
