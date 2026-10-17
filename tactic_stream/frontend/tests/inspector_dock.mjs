import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';
import vue from '@vitejs/plugin-vue';
import { chromium } from 'playwright';
const root = fileURLToPath(new URL('..', import.meta.url)),
  output = fileURLToPath(
    new URL('../../.screenshots/inspector-dock-current/', import.meta.url)
  );
const parents = [
  { __search_key__: 'cg/assets?id=1', code: 'A', name: 'Hero asset' },
  { __search_key__: 'cg/assets?id=2', code: 'B', name: 'Second asset' }
];
const users = [
  { value: 'alice', label: 'Alice Artist', displayName: 'Alice Artist' }
];
const fields = [
  'status',
  'assigned',
  'bid_start_date',
  'bid_end_date',
  'progress',
  'description'
].map((name) => ({ name, editable: true }));
const tasks = parents.map((parent, i) => ({
  __search_key__: 'sthpw/task?id=' + i,
  search_type: 'cg/assets',
  search_code: parent.code,
  process: 'model',
  context: 'model/main',
  status: 'In Progress',
  assigned: 'alice',
  bid_start_date: '2026-10-01 09:00:00',
  bid_end_date: '2026-10-20 18:00:00',
  progress: 30,
  description: 'Original description'
}));
const catalog = {
  users,
  processes: [{ value: 'model', label: 'Modeling' }],
  teams: [],
  milestoneChoices: [],
  priorityChoices: [],
  statuses: []
};
const html = `<!doctype html><html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body><div id="mobile-panel-picker"></div><div id="app"></div><script type="module">
import {createApp,h} from 'vue'
import App from '/src/App.vue'
import DockWorkspace from '/src/features/workspace/DockWorkspace.vue'
import HelpView from '/src/features/help/HelpView.vue'
import NotesPanel from '/src/features/objects/NotesPanel.vue'
import TaskManager from '/src/features/tasks/TaskManager.vue'
import {mobile} from '/src/mobile.js'
import {windowDirective} from '/src/controls/window.js'
import {appearance,initializeAppearance} from '/src/appearance.js'
import '/src/theme.css'
import '/src/style.css'
Object.assign(appearance,{mode:'dark',fadeAnimations:false,popupAnimations:false,clickAnimations:false});initializeAppearance();window.appearance=appearance
const parents=${JSON.stringify(parents)}
createApp({
 provide:App.provide,
 data(){return {session:{ticket:'fixture',login:'alice'},workspaceProject:'cg',workspaceView:{type:'cg/assets'},selectedRecords:[parents[0]],
 inspectorSource:null,inspectorTarget:null,inspectorRequest:0,inspectorReturn:'results',taskInspectorActive:false,canAdminister:true,taskCalendarActive:false,
 searchSaved:0,otherSaved:0,administrationOpen:false,administrationBlocked:false}},
 computed:{compactShortcuts(){return mobile.value}},
 methods:{openTaskInspector:App.methods.openTaskInspector,followInspector:App.methods.followInspector,openDock:App.methods.openDock,inspectorSaved:App.methods.inspectorSaved,reloadWorkspace(){},leaveAdministration(){if(!this.administrationBlocked)this.$refs.administrationDialog.close()}},
 mounted(){window.host=this},
 render(){return h('div',{style:'height:100dvh;position:relative;display:flex;flex-direction:column'},[
 h(HelpView,{ref:'help'}),
 h('dialog',{ref:'administrationDialog',onClose:()=>this.administrationOpen=false},'Administration fixture'),
 h(DockWorkspace,{ref:'docks',login:'inspector-test',mobile:mobile.value,canAdminister:true,
 onOpen:this.openDock,onChanged:()=>{this.taskInspectorActive=this.$refs.docks.presented('notes')},onHelp:topic=>this.$refs.help.open(topic)}),
 h(NotesPanel,{ref:'taskInspector',dockTarget:'#dock-notes',active:this.taskInspectorActive,ticket:this.session.ticket,project:this.inspectorSource?.project||this.workspaceProject,
 searchType:this.inspectorSource?.searchType||this.workspaceView.type,
 onBack:()=>this.$refs.docks.show(this.inspectorReturn||'results'),onVisibility:value=>value?this.$refs.docks.show('notes'):this.$refs.docks.hide('notes'),onSaved:this.inspectorSaved}),
 h(NotesPanel,{ref:'fromSearch',ticket:'fixture',project:'cg',searchType:'cg/assets',onSaved:()=>this.searchSaved++}),
 h(NotesPanel,{ref:'fromOther',ticket:'fixture',project:'other',searchType:'other/assets',onSaved:()=>this.otherSaved++}),
 h(TaskManager,{ref:'taskManager',docked:true,ticket:'fixture',project:'cg',currentUser:'alice',parents,searchType:'cg/assets',
 onOpened:()=>this.$refs.docks.show('tasks'),onTaskContext:task=>this.followInspector(task.parent,task.process,task.__search_key__)})
 ])}
}).directive('window',windowDirective).mount('#app')
</script></body></html>`;
const note = (parent, task, process) => ({
  id: 1,
  search_key: 'sthpw/note?id=1',
  target_key: task,
  login: 'alice',
  process,
  context: process,
  body: 'Note for ' + parent.name + noteSuffix,
  timestamp: '2026-10-12 12:00:00',
  attachments: [],
  can_change: true
});
let noteSuffix = '',
  privateFileRoute = null,
  holdPrivateFile = true;
let server,
  browser,
  slow = false,
  failRead = false,
  failNote = 0,
  held = [],
  saved = [],
  commands = [];
try {
  await mkdir(output, { recursive: true });
  server = await createServer({
    root,
    cacheDir: root + '/node_modules/.vite/inspector-dock',
    configFile: false,
    plugins: [
      vue(),
      {
        name: 'inspector-dock-fixture',
        configureServer(server) {
          server.middlewares.use(async (req, res, next) => {
            if (req.url !== '/inspector-test') return next();
            try {
              res.setHeader('Content-Type', 'text/html');
              res.end(await server.transformIndexHtml(req.url, html));
            } catch (error) {
              next(error);
            }
          });
        }
      }
    ],
    server: { host: '127.0.0.1', port: 0, watch: null }
  });
  await server.listen();
  browser = await chromium.launch({
    headless: true,
    channel: process.env.STREAM_BROWSER_CHANNEL || 'msedge'
  });
  const context = await browser.newContext({
      viewport: { width: 1280, height: 900 },
      hasTouch: true
    }),
    page = await context.newPage(),
    errors = [];
  page.setDefaultTimeout(10000);
  page.on('pageerror', (error) => {
    errors.push(error.message);
    console.error(error.message);
  });
  await page.addInitScript(() => {
    window.revokedNoteUrls = [];
    const revoke = URL.revokeObjectURL.bind(URL);
    URL.revokeObjectURL = (url) => {
      window.revokedNoteUrls.push(url);
      revoke(url);
    };
  });
  const privateKey = 'skey://sthpw/file?code=NOTE_PREVIEW';
  const image =
    '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>';
  await page.route('**/admin/navigation-link', (route) =>
    route.fulfill({
      json: {
        result: {
          previews: [
            {
              searchKey: privateKey,
              status: 'ready',
              kind: 'file',
              title: 'Private image.svg',
              previewUrl: '',
              privateAttachment: {
                chat: 'CHAT1',
                snapshot: {
                  code: 'S1',
                  __files__: [
                    { code: 'ICON1', type: 'icon' },
                    { code: 'F1', type: 'web' }
                  ]
                }
              }
            }
          ]
        }
      }
    })
  );
  await page.route('**/admin/messages/file', (route) => {
    if (holdPrivateFile) privateFileRoute = route;
    else return route.fulfill({ contentType: 'image/svg+xml', body: image });
  });

  await page.route('**/admin/workspace-layout/**', (route) =>
    route.fulfill({ json: { result: { presets: [], revision: 'layout' } } })
  );
  await page.route('**/admin/rpc', async (route) => {
    const payload = route.request().postDataJSON();
    commands.push(payload);
    const [auth, command, values] = payload.args;
    let info = {};
    if (command.endsWith('TaskInspectorCmd')) {
      const index = parents.findIndex(
          (p) => p.__search_key__ === values.search_key
        ),
        parent = parents[index < 0 ? 0 : index],
        task = tasks[index < 0 ? 0 : index];
      if (values.action === 'read') {
        if (failRead && values.search_key === parents[1].__search_key__) {
          failRead = false;
          await route.fulfill({
            status: 404,
            json: { error: 'Task not found' }
          });
          return;
        }
        info = {
          current_user: 'alice',
          search_key: values.search_key,
          process: values.process,
          process_type: 'task',
          selected_task: values.task_key || task.__search_key__,
          note_target: values.task_key || task.__search_key__,
          task_context: task.context,
          task: { ...task },
          revision: 'revision-' + parent.code,
          process_available: true,
          object: {
            record: parent,
            preview: { image: '' },
            search_type: 'cg/assets',
            type_title: 'Assets'
          },
          fields,
          users,
          statuses: ['In Progress', 'Complete'],
          status_choices: [
            { value: 'In Progress', label: 'In Progress', color: '#d8a95d' },
            { value: 'Complete', label: 'Complete', color: '#81af88' }
          ],
          processes: [
            {
              value: 'publish',
              label: 'Publish',
              type: 'built-in',
              count: 1,
              color: '#899bb5'
            },
            {
              value: 'model',
              label: 'Modeling',
              type: 'task',
              count: 1,
              color: '#789fd0'
            }
          ],
          task_choices: [
            {
              value: task.__search_key__,
              label: parent.name + ' / model',
              status: task.status,
              primary: true
            }
          ],
          notes: [note(parent, task.__search_key__, values.process)],
          history: [],
          identities: [
            { login: 'alice', displayName: 'Alice Artist', initials: 'AA' }
          ]
        };
        if (slow && values.search_key === parents[1].__search_key__) {
          held.push({ route, info });
          return;
        }
      } else if (values.action === 'save') {
        saved.push(payload);
        Object.assign(task, values.data);
        info = { task_key: task.__search_key__ };
      }
    } else if (command.endsWith('DiscussionChangeNoteCmd')) {
      saved.push(payload);
      if (failNote) {
        await route.fulfill({
          status: failNote,
          json: { error: 'Note write failed' }
        });
        return;
      }
      info = {};
    } else if (command.endsWith('DiscussionReadCmd'))
      info = { current_user: 'alice', notes: [], identities: [] };
    else if (command.endsWith('DiscussionAddNoteCmd')) {
      saved.push(payload);
      info = {};
    } else if (command.endsWith('TaskWorkspaceCmd'))
      info =
        values.action === 'catalog'
          ? catalog
          : {
              tasks,
              parents,
              total: tasks.length,
              loaded: tasks.length,
              offset: 0,
              hasMore: false,
              facets: {}
            };
    else if (command.endsWith('TaskWorkspaceEditCmd'))
      info = {
        plans:
          values.plans?.map((p) => ({
            operation: 'update',
            task_key: p.task_key,
            search_key: p.search_key,
            revision: 'original',
            task: tasks.find((t) => t.__search_key__ === p.task_key),
            data: {},
            fields,
            users,
            statuses: ['In Progress', 'Complete'],
            catalog
          })) || []
      };
    else if (command.endsWith('TaskMilestoneCmd')) info = { records: [] };
    await route.fulfill({ json: { result: { info } } });
  });
  await page.goto(server.resolvedUrls.local[0] + 'inspector-test');
  await page.waitForFunction(() => window.host);
  const panel = page.locator('[data-dock="notes"]'),
    inspector = panel.locator('section.notes-panel');
  const ready = () =>
    page.waitForFunction(
      () =>
        !!window.host.$refs.taskInspector.editor &&
        !window.host.$refs.taskInspector.loading &&
        !window.host.$refs.taskInspector.saving
    );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(
    await page.locator('dialog.notes-panel[open]').count(),
    0,
    'Inspector is a dock, not a modal'
  );
  assert.equal(
    await page.locator('section.notes-panel-docked').count(),
    1,
    'One Inspector owner for all entry points'
  );
  assert.equal(
    await inspector.locator('.inspector-window-header').count(),
    0,
    'Dock host owns window chrome'
  );
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=0'
  );
  assert.equal(
    commands.filter((p) => p.args[1].endsWith('TaskInspectorCmd')).length,
    1,
    'One read, without the process watcher selecting another task'
  );
  const readsBefore = commands.filter((p) =>
    p.args[1].endsWith('TaskInspectorCmd')
  ).length;
  await page.evaluate(
    (parent) =>
      window.host.openTaskInspector(
        parent,
        {},
        'model',
        'sthpw/task?project=cg&id=0',
        { project: 'cg' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(
    commands.filter((p) => p.args[1].endsWith('TaskInspectorCmd')).length,
    readsBefore,
    'Following the same canonical task context must retain its UI without another read'
  );
  const noteCard = inspector.locator('.shared-note-entry').first();
  await noteCard.getByText('Note for Hero asset', { exact: true }).waitFor();
  noteSuffix = ' ' + privateKey;
  const privateRequested = page.waitForRequest('**/admin/messages/file');
  await page.evaluate((key) => {
    const owner = window.host.$refs.taskInspector;
    owner.notes[0].body += ' ' + key;
    window.notePreviewLoad = owner.loadNotePreviews([key]);
  }, privateKey);
  const privateRequest = await privateRequested;
  assert.equal(privateRequest.postDataJSON().file_code, 'F1');
  await page.evaluate(() => window.host.$refs.taskInspector.load(true));
  await ready();
  holdPrivateFile = false;
  await privateFileRoute.fulfill({ contentType: 'image/svg+xml', body: image });
  await page.evaluate(() => window.notePreviewLoad);
  await page.waitForFunction(() => {
    const img = document.querySelector(
      '.shared-note-entry .skey-preview-card.file img'
    );
    return img?.complete && img.naturalWidth > 0;
  });
  const oldPreviewUrl = await page.evaluate(
    (key) => window.host.$refs.taskInspector.notePreviews[key].previewUrl,
    privateKey
  );
  await page.evaluate(
    (key) => window.host.$refs.taskInspector.loadNotePreviews([key], true),
    privateKey
  );
  assert.notEqual(
    await page.evaluate(
      (key) => window.host.$refs.taskInspector.notePreviews[key].previewUrl,
      privateKey
    ),
    oldPreviewUrl
  );
  assert(
    await page.evaluate(
      (url) => window.revokedNoteUrls.includes(url),
      oldPreviewUrl
    )
  );
  assert.equal(
    await page.evaluate(
      () => Object.keys(window.host.$refs.taskInspector.previewUrls).length
    ),
    1
  );
  noteSuffix = '';

  await noteCard.hover();
  await noteCard
    .getByRole('button', { name: 'Note actions', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Edit note', exact: true })
    .last()
    .click();
  const noteEditor = page.getByRole('dialog', {
    name: 'Edit note',
    exact: true
  });
  await noteEditor
    .getByLabel('Note text', { exact: true })
    .fill('Retained note edit');
  assert.equal(
    await noteEditor.evaluate((node) => node.matches(':modal')),
    false
  );
  await panel
    .getByRole('button', { name: 'Close panel: Task Inspector', exact: true })
    .click();
  await panel.waitFor({ state: 'hidden' });
  await noteEditor.waitFor({ state: 'hidden' });
  await page.evaluate(() => window.host.$refs.docks.show('notes'));
  await noteEditor.waitFor();
  assert.equal(
    await noteEditor.getByLabel('Note text', { exact: true }).inputValue(),
    'Retained note edit'
  );
  failNote = 409;
  await noteEditor.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(
    () =>
      !window.host.$refs.taskInspector.saving &&
      window.host.$refs.taskInspector.error === 'Note write failed'
  );
  assert.equal(
    await noteEditor
      .getByRole('textbox', { name: 'Error', exact: true })
      .inputValue(),
    'Note write failed'
  );
  assert.equal(
    await noteEditor.getByLabel('Note text', { exact: true }).inputValue(),
    'Retained note edit'
  );
  failNote = 502;
  await noteEditor.getByRole('button', { name: 'Save', exact: true }).click();
  await page.waitForFunction(() => window.host.$refs.taskInspector.uncertain);
  assert(
    await noteEditor
      .getByRole('button', { name: 'Save', exact: true })
      .isDisabled()
  );
  const writesBefore = saved.length;
  await page.evaluate(() =>
    window.host.$refs.taskInspector.change(
      window.host.$refs.taskInspector.editing.note,
      'edit'
    )
  );
  assert.equal(saved.length, writesBefore);
  await page
    .getByRole('dialog', { name: 'Edit note', exact: true })
    .getByRole('button', { name: 'Cancel', exact: true })
    .click();
  failNote = 0;
  await page.evaluate(() => window.host.$refs.taskInspector.load());
  await ready();
  await noteCard.hover();
  await noteCard
    .getByRole('button', { name: 'Note actions', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Delete note', exact: true })
    .last()
    .click();
  const deletion = page.getByRole('dialog', {
    name: 'Delete note?',
    exact: true
  });
  assert(await deletion.evaluate((node) => node.matches(':modal')));
  await deletion.getByRole('button', { name: 'Cancel', exact: true }).click();
  await noteCard.hover();
  await noteCard.getByRole('button', { name: 'Reply', exact: true }).click();
  await inspector
    .getByRole('button', { name: 'Cancel reply', exact: true })
    .click();
  const expand = inspector.getByRole('button', {
    name: 'Expand Task Inspector',
    exact: true
  });
  if (await expand.isVisible()) await expand.click();
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Asset A note draft');
  await page.evaluate(() =>
    window.host.$refs.taskInspector.stageTask(
      'description',
      'Asset A task draft'
    )
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
      ),
    parents[1]
  );
  await ready();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    ''
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  failRead = true;
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
      ),
    parents[1]
  );
  await inspector.getByRole('button', { name: 'Retry', exact: true }).waitFor();
  await page.evaluate(
    () => (window.host.$refs.taskInspector.draft.body = 'Keep this task draft')
  );
  assert(
    await inspector
      .getByRole('button', { name: 'Send note', exact: true })
      .isDisabled(),
    'A failed task read cannot send a note to the parent instead'
  );
  const savedBeforeRetry = saved.length;
  await page.evaluate(() => window.host.$refs.taskInspector.send());
  assert.equal(saved.length, savedBeforeRetry);
  await inspector.getByRole('button', { name: 'Retry', exact: true }).click();
  await ready();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Keep this task draft'
  );
  await inspector.getByLabel('Note text', { exact: true }).fill('');
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Asset A note draft'
  );
  assert.equal(
    await page.evaluate(
      () => window.host.$refs.taskInspector.taskDraft.description
    ),
    'Asset A task draft'
  );
  await inspector
    .getByRole('button', { name: /^Save task(?: changes)?$/, exact: true })
    .click();
  await ready();
  assert.equal(saved.at(-1).args[2].expected_revision, 'revision-A');
  assert.deepEqual(saved.at(-1).args[2].data, {
    description: 'Asset A task draft'
  });
  assert.equal(
    await page.evaluate(() => window.host.searchSaved),
    1,
    'Save notifies the original search owner'
  );
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Shared dock note');
  await inspector
    .getByRole('button', { name: 'Send note', exact: true })
    .click();
  await ready();
  assert.equal(await page.evaluate(() => window.host.searchSaved), 2);
  assert.equal(saved.at(-1).args[0].project, 'cg');
  await page.evaluate(() => window.host.$refs.taskManager.open());
  await page.waitForFunction(() => !window.host.$refs.taskManager.busy);
  await page.evaluate(() =>
    window.host.$refs.taskManager.inspect(
      window.host.$refs.taskManager.tasks[1]
    )
  );
  await ready();
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=1',
    'Task Manager opens the same dock with its exact task'
  );
  await page.evaluate(() => {
    window.host.$refs.docks.hide('notes');
    window.host.openDock('notes');
  });
  await ready();
  await page.waitForFunction(() => window.host.$refs.taskInspector.active);
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=1',
    'Reopening the dock keeps the last exact task'
  );
  await page.evaluate(() =>
    window.host.$refs.taskManager.activate('sthpw/task?id=0')
  );
  await ready();
  await page.waitForFunction(
    () => window.host.$refs.taskInspector.selectedTask === 'sthpw/task?id=0'
  );
  assert.equal(
    await inspector
      .locator('[data-frame="taskInspectorObjectTitle"]')
      .innerText(),
    'Hero asset',
    'Open Inspector follows active task selection'
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromOther.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(
    commands.at(-1).args[0].project,
    'other',
    'Source project is retained, rather than inferred from a visible tab'
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  await page.evaluate(
    () =>
      (window.host.$refs.taskInspector.editing = {
        note: { body: 'old' },
        body: 'unfinished'
      })
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
      ),
    parents[1]
  );
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=0',
    'Unfinished note edits are guarded on retarget'
  );
  await page.evaluate(() => (window.host.$refs.taskInspector.editing = null));
  slow = true;
  await page.evaluate((parent) => {
    window.pendingInspector = window.host.$refs.fromSearch.openTask(
      parent,
      {},
      { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
    );
  }, parents[1]);
  await page.waitForFunction(() => window.host.$refs.taskInspector.loading);
  for (let i = 0; i < 20 && !held.length; i++) await page.waitForTimeout(20);
  assert.equal(held.length, 1);
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  for (const item of held)
    await item.route.fulfill({ json: { result: { info: item.info } } });
  held = [];
  slow = false;
  await page.evaluate(() => window.pendingInspector);
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=0',
    'Late reads cannot replace the current target'
  );
  await page.evaluate(() => {
    window.host.administrationOpen = window.host.administrationBlocked = true;
    window.host.$refs.administrationDialog.showModal();
  });
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
      ),
    parents[1]
  );
  assert.equal(
    await page.evaluate(() => window.host.$refs.administrationDialog.open),
    true,
    'Administrative edit guards keep the modal open'
  );
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=0'
  );
  await page.evaluate(() => (window.host.administrationBlocked = false));
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=1' }
      ),
    parents[1]
  );
  await ready();
  assert.equal(
    await page.evaluate(() => window.host.$refs.administrationDialog.open),
    false,
    'Inspector leaves the modal before displaying a dock'
  );
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.selectedTask),
    'sthpw/task?id=1'
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  await page.evaluate(() => {
    window.host.$refs.docks.move('tasks', 'center', 'results');
    window.host.$refs.docks.move('notes', 'right', 'results');
  });
  await page.screenshot({ path: output + 'inspector-docked-dark.png' });
  // Use the public position menu for floating, then verify layout capture/restore.
  await panel
    .getByLabel('Panel position: Task Inspector', { exact: true })
    .click();
  await panel.getByRole('button', { name: 'Float panel', exact: true }).click();
  assert(await panel.evaluate((node) => node.classList.contains('floating')));
  const layout = await page.evaluate(() => window.host.$refs.docks.capture());
  assert.equal(
    layout.panels.find((p) => p.panel_id === 'notes').dock_area,
    'floating'
  );
  await page.waitForFunction(
    (node) => node.scrollWidth <= node.clientWidth,
    await inspector.elementHandle()
  );
  assert(
    await inspector.evaluate((node) => node.scrollWidth <= node.clientWidth)
  );
  await page.screenshot({ path: output + 'inspector-floating-dark.png' });
  await page.reload();
  await page.waitForFunction(() => window.host);
  await ready();
  assert(
    await panel.evaluate((node) => node.classList.contains('floating')),
    'Floating Inspector survives reload'
  );
  const restored = await page.evaluate(() =>
    window.host.$refs.docks.capture().panels.find((p) => p.panel_id === 'notes')
  );
  assert.equal(
    restored.width,
    layout.panels.find((p) => p.panel_id === 'notes').width
  );
  await panel
    .getByRole('button', { name: 'Close panel: Task Inspector', exact: true })
    .click();
  await panel.waitFor({ state: 'hidden' });
  await page.evaluate(() => window.host.$refs.docks.show('notes'));
  await panel.waitFor();
  assert(await inspector.getByLabel('Note text', { exact: true }).isVisible());
  await page.evaluate(() => {
    window.host.$refs.docks.move('notes', 'center', 'results');
    window.host.$refs.docks.move('tasks', 'right', 'results');
  });
  for (const theme of ['md3', 'material5'])
    for (const mode of ['light', 'dark']) {
      await page.evaluate(
        ({ theme, mode }) => Object.assign(window.appearance, { theme, mode }),
        { theme, mode }
      );
      await page.waitForFunction(
        (node) => node.scrollWidth <= node.clientWidth,
        await inspector.elementHandle()
      );
      assert(
        await inspector.evaluate((node) => node.scrollWidth <= node.clientWidth)
      );
      await page.screenshot({
        path: output + 'inspector-' + theme + '-' + mode + '.png'
      });
    }
  await page.setViewportSize({ width: 320, height: 740 });
  await page.evaluate(() => window.host.$refs.docks.show('tasks'));
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(await page.evaluate(() => window.host.inspectorReturn), 'tasks');
  await page.waitForFunction(
    (node) => node.scrollWidth <= node.clientWidth,
    await inspector.elementHandle()
  );
  assert(
    await inspector.evaluate((node) => node.scrollWidth <= node.clientWidth),
    'Phone Inspector fits its dock at 320px'
  );
  await inspector
    .getByLabel('Note text', { exact: true })
    .fill('Phone retained draft');
  await page.screenshot({ path: output + 'inspector-phone-320.png' });
  await panel.getByRole('button', { name: 'Help', exact: true }).tap();
  const help = page.locator('dialog.help-view[open]');
  await help.waitFor();
  await help.getByRole('button', { name: 'Close help', exact: true }).tap();
  await help.waitFor({ state: 'hidden' });
  await panel.getByRole('button', { name: 'Back', exact: true }).tap();
  await panel.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(() => window.host.$refs.docks.presented('tasks')),
    true,
    'Phone Back returns to the originating Task Manager'
  );
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  assert.equal(
    await inspector.getByLabel('Note text', { exact: true }).inputValue(),
    'Phone retained draft'
  );
  await page.evaluate(
    (parent) => window.host.$refs.fromSearch.open(parent, {}, 'publish', false),
    parents[0]
  );
  const standalone = page.getByRole('dialog', { name: 'Notes', exact: true });
  await standalone.waitFor();
  assert.equal(
    await page.locator('dialog[open][aria-label="Task Inspector"]').count(),
    0,
    'Separate Notes remains optional; Inspector stays docked'
  );
  await standalone.getByRole('button', { name: 'Back', exact: true }).tap();
  await page.evaluate(
    (parent) =>
      window.host.$refs.fromSearch.openTask(
        parent,
        {},
        { process: 'model', taskSearchKey: 'sthpw/task?id=0' }
      ),
    parents[0]
  );
  await ready();
  await noteCard.hover();
  await noteCard
    .getByRole('button', { name: 'Note actions', exact: true })
    .click();
  await page
    .getByRole('button', { name: 'Edit note', exact: true })
    .last()
    .click();
  await noteEditor.waitFor();
  await page.evaluate(() => {
    window.host.inspectorSource = {
      ...window.host.inspectorSource,
      project: 'other'
    };
  });
  await noteEditor.waitFor({ state: 'hidden' });
  assert.equal(
    await page.evaluate(() => window.host.$refs.taskInspector.editing),
    null
  );
  assert.deepEqual(errors, []);
  console.log(
    'Inspector dock: one owner, exact task/project, drafts/revisions, original save callbacks, selection, guarded/stale reads, float/stack/restore, themes, phone Back/Help and optional Notes OK'
  );
} finally {
  for (const item of held) await item.route.abort().catch(() => {});
  await browser?.close();
  await server?.close();
}
