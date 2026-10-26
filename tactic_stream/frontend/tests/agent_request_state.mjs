import assert from 'node:assert/strict';
import { randomUuid } from '../src/controls/identity.js';
import * as UI from '../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';

const crypto = globalThis.crypto;
Object.defineProperty(globalThis, 'crypto', { value: { getRandomValues: values => crypto.getRandomValues(values) }, configurable: true });
const ids = Array.from({ length: 1000 }, randomUuid);
assert.equal(new Set(ids).size, ids.length);
assert.ok(ids.every(value => /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(value)));
Object.defineProperty(globalThis, 'crypto', { value: crypto, configurable: true });
const model = UI.initial({ client: 'TS', project: 'one', page: 'shots', title: 'Shots', search_type: 'cg/shot', view: 'table', search_keys: ['cg/shot?project=one&code=SH001'] });
model.prompt = 'Make a page';
assert.equal(UI.canSend(model), false);
model.hosts = [{ host_id: 'one', label: 'Codex', capabilities: { changes: false } }];
assert.equal(UI.canSend(model), true);
model.allowChanges = true;
assert.equal(UI.canSend(model), false);
model.hosts[0].capabilities.changes = true;
assert.equal(UI.canSend(model), true);
model.selected = 'sent';
assert.equal(UI.canSend(model), false);
model.request = { status: 'running', document: { context: model.context, prompt: model.prompt, allow_changes: true } };
assert.equal(UI.active(model), true);
for (const width of [320, 520, 1000]) {
  const scene = UI.describe(model, width, 650, 'ru');
  assert.ok(scene.nodes.every(node => node.x >= 0 && node.x + node.width <= width));
  assert.equal(scene.nodes.find(node => node.id === 'agentRequestContext').context.search_keys.length, 1);
  model.contextExpanded = true;
  assert.ok(UI.describe(model, width, 650, 'ru').nodes.find(node => node.id === 'agentRequestContext').context.search_keys[0].includes('SH001'));
  model.contextExpanded = false;
}
console.log('Request permissions, captured context, narrow layout and LAN HTTP UUID generation passed');
