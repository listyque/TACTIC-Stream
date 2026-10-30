import assert from 'node:assert/strict';
import {
  current,
  controls
} from '../../src/tactic_stream/shared_ui/features/scripts/executor.ui.mjs';

const desktop = {
  id: 'desktop',
  kind: 'desktop',
  label: 'Workstation',
  state: 'stopped'
};
const server = {
  id: 'server',
  kind: 'server',
  label: 'TACTIC server',
  state: 'stopped'
};
const model = { executor: { targets: [server] }, executorTarget: null };
assert.equal(current(model).target, '');
assert.equal(controls(model, 1000, 0, 'en')[1].enabled, false);
model.executor = { targets: [desktop, server], preferred: 'desktop' };
assert.equal(current(model).target, 'desktop');
model.executorTarget = 'server';
assert.equal(current(model).target, 'server');
desktop.state = 'connected';
assert.equal(current(model).unavailable, true);
model.executorTarget = null;
assert.equal(current(model).target, 'desktop');
model.executor.targets = [server];
model.executorTarget = 'desktop';
assert.equal(current(model).unavailable, true);
assert.equal(controls(model, 1000, 0, 'en')[1].enabled, false);
for (const width of [320, 480, 1000]) {
  const nodes = controls(model, width, 0, 'en');
  for (const node of nodes.filter((item) => item.visible !== false)) {
    assert(node.x >= 0 && node.width >= 0 && node.x + node.width <= width);
  }
}
console.log(
  'PASS: explicit execution targets, local preference, disconnects and narrow layout'
);
