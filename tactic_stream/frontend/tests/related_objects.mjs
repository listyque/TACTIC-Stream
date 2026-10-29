import assert from 'node:assert/strict';
import {
  menuActions,
  toolbar
} from '../../src/tactic_stream/shared_ui/features/objects/related.ui.mjs';

const item = {
  title: 'Assets',
  command: 'related:child:cg/assets',
  accent: '#f44',
  translate: false
};
const source = [item];
const menu = menuActions(source);
assert.equal(source.length, 1);
assert.equal(menu[0], item);
assert.equal(menu.at(-1).command, 'open_related_objects');
assert.equal(menuActions(menu).length, menu.length);
assert.equal(menuActions([]).length, 1);

for (const language of ['en', 'ru']) {
  for (const width of [320, 600, 1120]) {
    const scene = toolbar(
      {
        parentTitle: 'Episode 01',
        relations: [{ value: 'cg/shot', label: 'Shot' }],
        selectedType: 'cg/shot',
        canCreate: true
      },
      width,
      language
    );
    const choice = scene.nodes.find((node) => node.id === 'relatedType');
    const create = scene.nodes.find((node) => node.id === 'relatedCreate');
    assert.equal(choice.value, 'cg/shot');
    assert.equal(choice.options[0].label, 'Shot');
    assert.ok(choice.x + choice.width <= width - 12);
    assert.ok(create.x + create.width <= width - 12);
    assert.ok(
      create.y >= choice.y + choice.height ||
        create.x >= choice.x + choice.width
    );
    assert.ok(create.y + create.height <= scene.height);
  }
}
const readOnly = toolbar({ relations: [], canCreate: false }, 320, 'en');
assert.equal(
  readOnly.nodes.find((node) => node.id === 'relatedType').enabled,
  false
);
assert.equal(
  readOnly.nodes.some((node) => node.id === 'relatedCreate'),
  false
);
console.log('Related menu and responsive toolbar contracts passed');
