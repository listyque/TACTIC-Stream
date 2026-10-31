import assert from 'node:assert/strict';
import * as Settings from '../../src/tactic_stream/shared_ui/features/configuration/settings.ui.mjs';
import * as Editor from '../../src/tactic_stream/shared_ui/features/scripts/editor.ui.mjs';

for (const streamApi of [false, true]) {
  const fields = Settings.fieldsFor('server', { native: true, streamApi, values: {} });
  assert(fields.some((field) => field.field === 'serverUrl'));
  for (const name of ['serverUpdateMode', 'serverUpdateBatchDelay'])
    assert.equal(fields.some((field) => field.field === name), streamApi);
  for (const native of [true, false]) {
    const toolbar = Editor.toolbar({ native, streamApi, source: '', canEdit: true }, 1000, 'en');
    assert(toolbar.nodes.some((node) => node.id === 'script_triggers'));
    assert.equal(toolbar.nodes.some((node) => node.id === 'script_drafts'), !native || streamApi);
  }
}
console.log('PASS: legacy native settings/drafts hidden; normal native controls and Stream browser actions preserved');
