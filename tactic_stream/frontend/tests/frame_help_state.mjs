import assert from 'node:assert/strict';
import * as State from '../../src/tactic_stream/shared_ui/features/support/help/help.state.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/support/help/help.ui.mjs';
import {
  validateScene,
  listRowHeight
} from '../../src/tactic_stream/shared_ui/core/frame.mjs';

const articles = [
  {
    id: 'overview',
    title: 'Overview',
    group: 'Guide',
    searchText: 'intro',
    icon: 'help',
    file: '/overview.en.md'
  },
  {
    id: 'windows',
    title: 'Windows',
    group: 'Guide',
    searchText: 'owner focus resize',
    icon: 'window',
    file: '/windows.en.md'
  }
];
let model = State.initial();
function dispatch(action) {
  const result = State.transition(model, articles, action);
  model = result.model;
  return result.commands;
}
dispatch({ type: 'query', value: 'intro' });
dispatch({ type: 'scroll', id: 'overview', value: 430 });
dispatch({ type: 'open' });
assert.equal(model.query, 'intro');
assert.equal(State.offset(model, 'overview'), 430);
dispatch({ type: 'select', id: 'windows' });
assert.equal(
  model.query,
  '',
  'An explicit topic outside the filter reveals itself'
);
dispatch({ type: 'scroll', id: 'overview', value: 0 });
assert.equal(
  State.offset(model, 'overview'),
  430,
  'Late events cannot erase another document position'
);
dispatch({ type: 'select', id: 'overview' });
assert.equal(State.offset(model, 'overview'), 430);
assert.deepEqual(dispatch({ type: 'topicKey', id: 'overview', key: 'End' }), [
  { type: 'focusTopic', id: 'windows' }
]);
dispatch({ type: 'topics', value: true });
assert(
  dispatch({ type: 'select', id: 'windows' }).some(
    (command) => command.type === 'focusArticle'
  ),
  'Closing the phone topic list returns keyboard ownership to the reader'
);
dispatch({ type: 'select', id: 'overview' });
dispatch({ type: 'loaded' });
assert.equal(State.offset(model, 'overview'), 430);
assert.equal(
  State.topicFromLink('file:///docs/windows.ru.md#resize'),
  'windows'
);
assert.equal(State.topicFromLink('https://example.test/'), '');
for (const width of [320, 360, 760, 1100]) {
  const scene = UI.describe(
    model,
    { articles, canDownload: true },
    width,
    700,
    'en'
  );
  validateScene(
    scene,
    { helpTopics: scene.topicRows },
    { document: {}, busy: {} }
  );
  for (const box of scene.nodes) assert(box.x + box.width <= width, box.id);
  const list = scene.nodes
    .find((node) => node.id === 'helpTopicsPanel')
    .children.find((node) => node.id === 'helpTopicList');
  assert.equal(
    listRowHeight(list),
    UI.topicRow(model, articles[0], 220, 'en').nodes[0].height,
    'Topic cards fit their list row without one clipped pixel'
  );
  for (const record of scene.topicRows)
    validateScene(UI.topicRow(model, record, 220, 'en'));
}
console.log(
  'Help state: filter, context, scroll positions, late events, navigation and phone/desktop scenes passed.'
);
