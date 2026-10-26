import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as Providers from '../../src/tactic_stream/shared_ui/features/configuration/providers.ui.mjs';
import * as Request from '../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';

const profiles = [
  { id: 'codex', name: 'Codex', kind: 'codex', url: '', enabled: true, status: 'connected', models: [] },
  { id: 'local', name: 'Local fixture', kind: 'local', url: 'http://127.0.0.1:11434/v1', enabled: true, status: 'unchecked', models: [{ id: 'm', label: 'Fixture model' }] }
];
let settings = Providers.select({ ...Providers.initial(), profiles, kinds: profiles.map(row => ({ value: row.kind, label: row.name, url: row.url })) }, 'local');
assert.equal(Providers.dirty(settings), false);
settings = Providers.edit(settings, 'secret', 'private-fixture');
assert.equal(Providers.dirty(settings), true);
const node = (nodes, id) => nodes.find(item => item.id === id) || nodes.flatMap(item => item.children || []).map(item => item.id === id ? item : node([item], id)).find(Boolean);
for (const width of [320, 520, 1000]) {
  for (const language of ['en', 'ru']) {
    const scene = Providers.describe(settings, width, 650, language);
    validateScene(scene);
    assert.equal(node(scene.nodes, 'setting_secret').password, true);
    assert.equal(node(scene.nodes, 'agentProviderCheck').enabled, false);
    assert.ok(scene.nodes.every(item => item.x >= 0 && item.x + item.width <= width));
  }
}
const model = Request.initial({ client: 'TS', project: 'one', search_keys: [] });
model.prompt = 'Read the project';
model.hosts = [{ host_id: 'h', capabilities: { changes: true, providers: profiles, default_provider: 'local', models: [
  { id: 'same', label: 'Account model', provider: 'codex', efforts: ['high'], is_default: true },
  { id: 'same', label: 'Local model', provider: 'local', efforts: [], is_default: true }
] } }];
assert.equal(Request.provider(model), 'local');
assert.deepEqual(Request.availableModels(model).map(row => row.label), ['Local model']);
assert.equal(Request.canSend(model), true);
model.provider = 'codex';
assert.deepEqual(Request.availableModels(model).map(row => row.label), ['Account model']);
model.selected = 'old';model.request = { request_id: 'old', status: 'completed', provider: 'local', document: { context: model.context } };
model.provider = null;
assert.equal(Request.provider(model), 'local');
model.request.provider = 'unavailable';
assert.equal(Request.canSend(model), false);
console.log('Provider write-only fields, drafts, narrow layouts and provider-scoped model selection passed');
