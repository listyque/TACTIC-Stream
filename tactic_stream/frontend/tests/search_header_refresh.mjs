import assert from 'node:assert/strict';
import { describe } from '../../src/tactic_stream/shared_ui/features/search/header.ui.mjs';

for (const reserveGrip of [true, false]) {
  for (const width of [320, 430, 719, 720, 900]) {
    for (const busy of [true, false]) {
      const scene = describe(
        { compact: width < 720, reserveGrip, busy },
        width,
        'ru'
      );
      const refresh = scene.nodes.find(
        (node) => node.id === 'searchRefreshButton'
      );
      const field = scene.nodes.find((node) => node.id === 'searchHeaderField');
      assert.equal(refresh.visible, true);
      assert.equal(refresh.enabled, !busy);
      assert.equal(refresh.action.type, 'refresh');
      assert(refresh.x >= 0 && refresh.x + refresh.width <= field.x);
      assert(field.width > 0 && field.x + field.width <= width);
    }
  }
}
for (const searchOpen of [true, false]) {
  const scene = describe(
    { compact: true, collapseSearch: true, searchOpen },
    320,
    'en'
  );
  for (const id of ['searchRefreshButton', 'searchHeaderField']) {
    assert.equal(
      scene.nodes.find((node) => node.id === id).visible,
      searchOpen
    );
  }
}
console.log(
  'Search refresh: narrow/wide geometry, loading and collapsed mobile search passed'
);
