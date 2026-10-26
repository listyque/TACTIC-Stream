import assert from 'node:assert/strict';
import { validateScene } from '../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as UI from '../../src/tactic_stream/shared_ui/features/scripts/request.ui.mjs';
import * as History from '../../src/tactic_stream/shared_ui/features/scripts/history.ui.mjs';

const now = new Date(2026, 9, 26, 12).getTime();
const model = UI.initial({ client: 'TS', project: 'one', page: 'shots', title: 'Shots', search_type: 'cg/shot', view: 'table', search_keys: [] });
model.groups = [{ id: 'folder', name: 'Production' }];
model.groups_revision = 'g1';
model.requests = [0, 1, 3, 10, 60].map((days, index) => ({ request_id: 'chat-' + index, title: 'Chat ' + index,
  prompt: 'Original request ' + index, status: 'completed', activity: now / 1000 - days * 86400,
  search_type: index % 2 ? 'cg/shot' : 'cg/assets', type_title: index % 2 ? 'Shots' : 'Assets',
  pinned: index === 4, group: index < 2 ? 'folder' : '', archived: false, library_revision: 'r' + index }));
for (const width of [320, 520, 1000, 1400]) for (const language of ['en', 'ru']) for (const visible of [null, true, false]) {
  model.history.visible = visible;
  const records = History.rows(model, language, now);
  validateScene(UI.describe(model, width, 650, language), { agentHistoryRows: records });
  const space = History.layout(model, width);
  assert.ok(space.mainWidth >= 0 && space.panel >= 0 && space.panel <= width);
  for (const record of records) validateScene(History.row(model, record, Math.max(200, space.panel - 16), language));
}
model.history = History.initial();
assert.deepEqual(History.rows(model, 'en', now).filter(row => row.kind === 'heading').map(row => row.title), ['Pinned conversations', 'Today', 'Yesterday', 'Previous 7 days', 'Previous 30 days']);
model.history.grouping = 'type';
assert.ok(History.rows(model, 'en', now).some(row => row.title === 'Shots'));
model.history.grouping = 'group';
assert.ok(History.rows(model, 'en', now).some(row => row.title === 'Production'));
model.history = History.change(model, { type: 'historyEdit', value: 'chat-0' });
assert.equal(model.history.edit.title, 'Chat 0');
assert.equal(model.history.edit.revision, 'r0');
for (const language of ['en', 'ru']) validateScene(History.describe(model, 280, 650, language, false));
model.history = History.change(model, { type: 'historyGroupEdit', value: 'folder' });
assert.equal(model.history.edit.name, 'Production');
model.history = History.change(model, { type: 'historyRemoveConfirm' });
validateScene(History.describe(model, 280, 650, 'ru', false));
assert.equal(model.history.edit.confirm, true);
model.selected = 'draft';model.request = { request_id: 'draft', status: 'draft', document: { context: model.context } };
assert.equal(UI.started(model), false);
assert.deepEqual(UI.messages(model), []);
model.prompt = 'Unsent message';model.attachments = [{ attachment_id: 'file' }];
assert.deepEqual(History.restored(History.draft(model)).attachments, model.attachments);
const foreign = {...model.requests[0], project:'other', project_title:'Other project'};
model.requests.push(foreign);
assert.notEqual(History.key(foreign),History.key(model.requests[0],model.context.project));
assert.equal(History.selection(model,{request_id:foreign.request_id,project:'other'}),foreign);
model.history=History.change(model,{type:'historyProject',value:'other'});
assert.equal(model.context.project,'one');
assert.equal(model.history.project,'other');
assert.deepEqual(History.projectContext({...model.context,search_keys:['old-selection']},'other').search_keys,[]);
model.groups=[{id:'folder',name:'Other folder',project:'other'}];
model.group_revisions={other:'other-revision'};
model.history=History.change(model,{type:'historyGroupEdit',value:{id:'folder',project:'other'}});
assert.equal(model.history.edit.revision,'other-revision');
console.log('History dates, types, folders, pins, editors, virtual rows, drafts and responsive scenes passed');
