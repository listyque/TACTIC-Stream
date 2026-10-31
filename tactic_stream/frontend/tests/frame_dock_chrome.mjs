import assert from 'node:assert/strict';
import {
  describe,
  positions
} from '../../src/tactic_stream/shared_ui/shell/dock_chrome.ui.mjs';

const native = { separateWindow: true, queueOwnChrome: true };
const browser = {
  maximize: true,
  positionMenu: true,
  floatingResultsTitle: true,
  resultsActions: true
};
for (const capabilities of [native, browser])
  for (const kind of ['results', 'description', 'commit_queue']) {
    for (const stackSize of [1, 3])
      for (const floating of [false, true])
        for (const width of [280, 500, 1280]) {
          const scene = describe({
            width,
            kind,
            stackSize,
            floating,
            capabilities,
            closable: kind !== 'results'
          });
          const controls = positions(scene);
          for (const id of [
            'dockHelp',
            'dockMaximize',
            'dockPosition',
            'dockDetach',
            'dockClose'
          ]) {
            assert.equal(controls[id].round, true, id);
            assert.equal(controls[id].width, controls[id].height, id);
          }
          assert.equal(controls.dockGrip.round, false);
          assert.equal(controls.dockTabs.visible, stackSize > 1);
          assert.equal(controls.dockTitle.visible, stackSize <= 1);
          assert.equal(controls.dockClose.visible, kind !== 'results');
          assert.equal(
            controls.dockDetach.visible,
            kind !== 'results' && !!capabilities.separateWindow
          );
          if (scene.height === 0) continue;
          const visible = scene.nodes.filter((node) => node.visible !== false);
          for (const node of visible)
            assert(
              node.x >= 0 &&
                node.x + node.width <= width &&
                node.y >= 0 &&
                node.y + node.height <= scene.height,
              node.id
            );
          const actions = visible.filter(
            (node) => !['dockTabs', 'dockIcon', 'dockTitle'].includes(node.id)
          );
          for (let index = 1; index < actions.length; index++)
            assert(
              actions[index].x >=
                actions[index - 1].x + actions[index - 1].width
            );
          const label = stackSize > 1 ? controls.dockTabs : controls.dockTitle;
          if (actions.length)
            assert(
              label.x + label.width <= actions[0].x - 8,
              'Tabs cannot cover action hit areas'
            );
        }
  }
console.log(
  'Dock chrome: native/browser capabilities, headers, floating Results, stacks and non-overlapping actions passed'
);
