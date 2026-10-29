import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import {
  choice,
  choiceLayout,
  choiceStyle
} from '../../src/tactic_stream/shared_ui/features/tasks/cells.ui.mjs';

let states = 0;
for (const avatar of [false, true])
  for (const indicator of [false, true])
    for (const showAccent of [false, true])
      for (const enabled of [false, true])
        for (const hovered of [false, true])
          for (const actionField of [false, true])
            for (const fontRole of ['body', 'caption'])
              for (const height of [0, 10, 17.5, 24, 29])
                for (const width of [0, 99, 240]) {
                  const model = {
                    avatar,
                    indicator,
                    showAccent,
                    enabled,
                    hovered,
                    actionField,
                    fontRole,
                    text: 'Artist',
                    accent: '#3fab76'
                  };
                  const layout = choiceLayout(model, width, height);
                  const style = choiceStyle(model);
                  const scene = choice(model, width, height);
                  validateScene(scene, {}, avatar ? { avatar: true } : {});
                  const label = scene.nodes.find(
                    (node) => node.id === 'taskTableCellDisplayLabel'
                  );
                  for (const field of [
                    'x',
                    'y',
                    'width',
                    'height',
                    'fontSize',
                    'weight'
                  ])
                    assert.equal(label[field], layout.label[field]);
                  assert.equal(label.text, model.text);
                  assert.equal(
                    label.color,
                    enabled ? 'primaryText' : 'disabledText'
                  );
                  assert.equal(scene.nodes[0].background, style.background);
                  assert.equal(
                    scene.nodes[0].border,
                    actionField ? undefined : 'outlineVariant'
                  );
                  assert.equal(Boolean(layout.avatar), avatar);
                  assert.equal(Boolean(layout.accent), showAccent);
                  assert.equal(Boolean(layout.indicator), indicator);
                  assert.deepEqual(
                    choiceLayout(
                      { ...model, hovered: !hovered, enabled: !enabled },
                      width,
                      height
                    ),
                    layout
                  );
                  states++;
                }
assert.throws(
  () => choiceLayout({ fontRole: 'missing', textHeight: 14 }, 99, 29),
  /font role/
);
assert.throws(
  () => choiceLayout({}, Number.POSITIVE_INFINITY, 29),
  /Invalid frame/
);
console.log(
  'PASS shared task value geometry, paint, validation and scene agreement:',
  states
);
