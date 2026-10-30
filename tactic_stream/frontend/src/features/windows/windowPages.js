import { markRaw, nextTick, toRaw } from 'vue';
import { notify } from '../activity/notifications.js';
import { randomUuid } from '../../controls/identity.js';
import { navigationLink, projectCreationCatalog } from '../../api.js';
import { fileBlob } from '../objects/previewFiles.js';

// Existing window owners keep their controllers, authorization and close guards.
export const windowPages = {
  messages: { ref: 'messages' },
  work_hours: { load: () => import('../objects/Timesheet.vue') },
  snapshot_browser: {
    open: async (app, context) => {
      app.snapshotTarget = {
        project: context.project,
        ...context.route.target
      };
      app.snapshotMounted = app.snapshotActive = true;
      await nextTick();
      app.$refs.snapshotPage.show();
    }
  },
  sobject_info: {
    open: (app, context) => app.inspect({ __search_key__: context.route.key })
  },
  file_preview: {
    open: async (app, context) => {
      if (context.state) {
        const { record, cell, download } = context.state;
        app.$refs.linkPreview.open(record, {
          ...cell,
          ...(download ? { loadFile: fileBlob } : {})
        });
      } else {
        const result = await navigationLink(
          app.session.ticket,
          context.project,
          'skey://' + context.route.key
        );
        if (!result.preview) throw Error('No preview available');
        app.$refs.linkPreview.open(result.object, {
          ...result.preview,
          fileCode: context.route.fileCode,
          loadFile: fileBlob
        });
      }
    }
  },
  related_objects: { load: () => import('../objects/RelatedObjects.vue') },
  link_sobjects: { load: () => import('../objects/RelatedObjects.vue') },
  add_sobject: { load: () => import('../objects/RecordForm.vue') },
  task_editor: { load: () => import('../objects/RecordForm.vue') },
  process_dependencies: {
    load: () => import('../administration/ProcessRules.vue')
  },
  duplicate_sobject: {
    load: () => import('../objects/DuplicateSObject.vue'),
    args: (context) => [{ __search_key__: context.route.key }, false]
  },
  ingest_files: { load: () => import('../checkin/IngestFiles.vue') },
  snapshot_append: {
    load: () => import('../checkin/ObjectCheckin.vue'),
    args: (context) => [{ __search_key__: context.route.key }, { append: true }]
  },
  project_templates: { load: () => import('../projects/ProjectTemplates.vue') },
  milestone_manager: { load: () => import('../tasks/MilestoneManager.vue') },
  snapshot_checkout: { load: () => import('../checkin/SnapshotCheckout.vue') },
  task_manager: {
    ref: 'taskManager',
    open: (app, context) =>
      app.$refs.taskManager.open(...(context.args || context.route.args || []))
  },
  user_profile: { ref: 'userProfile' },
  activity_feed: { ref: 'activityFeed' },
  notifications: { ref: 'systemActivity' },
  debug_log: { ref: 'debugLog' },
  ui_performance: { ref: 'uiPerformance' },
  system_info: { ref: 'systemInfo' },
  help: { ref: 'help' },
  script_shelf_editor: { ref: 'scriptShelf' },
  project_wizard: { ref: 'projectCreation' },
  configuration: {
    open: async (app) => {
      await app.$options.components.Configuration.__asyncLoader();
      await app.showConfiguration();
    },
    ref: 'configuration'
  },
  administration: {
    open: (app, context) =>
      app.showAdministration(context.route?.section || null)
  },
  script_editor: {
    open: (app, context) => app.openScriptEditor(context.route?.path || ''),
    ref: 'scriptEditor'
  },
  agent_request: {
    open: (app, context) => app.openAgentRequest(null, context.project),
    ref: 'agentRequest'
  },
  agent_providers: {
    open: (app) => app.openAgentProviders(),
    ref: 'agentProviders'
  },
  agent_mcp: {
    open: (app, context) =>
      app.openAgentMcp(
        context.args?.[0] || context.route.args?.[0] || app.agentContext(),
        context.args?.[1] || context.route.args?.[1] || ''
      ),
    ref: 'agentMcp'
  }
};

export function windowPageAddress(kind, project = '', route = {}) {
  if (!Object.hasOwn(windowPages, kind))
    throw Error('This window cannot be opened separately.');
  const encoded = JSON.stringify(route);
  if (
    !route ||
    typeof route !== 'object' ||
    Array.isArray(route) ||
    encoded.length > 8192
  )
    throw Error('This window cannot be opened separately.');
  const url = new URL(
    project ? '/projects/' + encodeURIComponent(project) + '/' : '/',
    location.origin
  );
  url.searchParams.set('window', kind);
  if (Object.keys(route).length) url.searchParams.set('context', encoded);
  return url;
}
export function readWindowPage(address = location) {
  const params = new URLSearchParams(address.search);
  if (!params.has('window')) return null;
  const kind = params.get('window'),
    encoded = params.get('context') || '{}';
  const match = address.pathname.match(/^\/projects\/([^/]+)\/$/);
  let route,
    project = '';
  try {
    project = match ? decodeURIComponent(match[1]) : '';
    route = encoded.length <= 8192 ? JSON.parse(encoded) : null;
  } catch {
    route = null;
  }
  return {
    kind,
    project,
    route,
    launch: params.get('launch') || ''
  };
}

function snapshot(value) {
  const raw = toRaw(value);
  if (raw instanceof Blob) return raw;
  if (Array.isArray(raw)) return raw.map(snapshot);
  if (raw && typeof raw === 'object')
    return Object.fromEntries(
      Object.entries(raw).map(([key, item]) => [key, snapshot(item)])
    );
  if (typeof raw === 'function')
    throw Error('Window context must contain data only.');
  return raw;
}
function receiveContext(page, login) {
  if (!page.launch) return Promise.resolve(page);
  return new Promise((resolve, reject) => {
    const channel = new BroadcastChannel('tactic-window:' + page.launch);
    const done = (value, error) => {
      clearInterval(retry);
      clearTimeout(deadline);
      channel.close();
      if (error) reject(Error(error));
      else resolve(value);
    };
    channel.onmessage = (event) => {
      if (event.data?.type === 'context') {
        const value = event.data.value;
        if (
          value.user !== login ||
          value.kind !== page.kind ||
          value.project !== page.project
        )
          return done(
            null,
            'The window session or project changed. Reopen it from the original window.'
          );
        channel.postMessage({ type: 'accepted' });
        done(value);
      } else if (event.data?.type === 'error') done(null, event.data.message);
    };
    const ready = () => channel.postMessage({ type: 'ready', login });
    const retry = setInterval(ready, 500);
    const deadline = setTimeout(
      () =>
        done(
          null,
          'The original window is unavailable. Reopen this page from the application.'
        ),
      15000
    );
    ready();
  });
}

export async function openWindowPageTarget(app, context) {
  const spec = windowPages[context.kind];
  if (
    !spec ||
    !context.route ||
    typeof context.route !== 'object' ||
    Array.isArray(context.route)
  )
    throw Error('This window cannot be opened separately.');
  if (spec.load) {
    const session = app.session;
    const module = await spec.load();
    if (app.session !== session) return;
    if (context.kind === 'project_templates')
      app.windowPagePackages = (
        await projectCreationCatalog(session.ticket)
      ).installedTemplates;
    if (app.session !== session) return;
    app.windowPageTool = markRaw(module.default);
    const values = {
      ticket: session.ticket,
      project: app.workspaceProject,
      currentUser: session.login,
      searchType: context.route.searchType || app.type,
      editView: context.route.editView || 'edit',
      insertView: context.route.insertView || 'insert',
      packages: app.windowPagePackages,
      dockMode:
        context.kind === 'work_hours' ? context.route.mode || 'week' : undefined
    };
    app.windowPageToolProps = Object.fromEntries(
      Object.entries(values).filter(([key]) =>
        Object.hasOwn(module.default.props || {}, key)
      )
    );
    await nextTick();
    await app.$refs.windowPageTool.open(
      ...(spec.args
        ? spec.args(context)
        : context.args || context.route.args || [])
    );
    if (context.state)
      await app.$refs.windowPageTool.restoreWindowContext?.(context.state);
  } else if (spec.open) await spec.open(app, context);
  else
    await app.$refs[spec.ref].open(
      ...(context.args || context.route.args || [])
    );
  await nextTick();
  if (context.kind === 'configuration' && context.route.page)
    await app.$refs.configuration.restoreWindowContext({
      page: context.route.page
    });
  if (
    context.kind === 'agent_request' &&
    context.route.request &&
    !context.state
  )
    context.state = { selected: context.route.request };
  if (spec.ref && context.state)
    await app.$refs[spec.ref]?.restoreWindowContext?.(context.state);
}

export async function bootstrapWindowPage(app) {
  const page = app.windowPage;
  if (
    !Object.hasOwn(windowPages, page.kind) ||
    !page.route ||
    typeof page.route !== 'object' ||
    Array.isArray(page.route)
  )
    throw Error('This window cannot be opened separately.');
  if (
    page.project &&
    !app.projects.some((project) => project.code === page.project)
  )
    throw Error('Project is not available');
  const session = app.session;
  const context = await receiveContext(page, session.login);
  if (app.session !== session) return;
  app.windowPageContext = context;
  app.project = app.workspaceProject = page.project;
  app.type = context.workspace?.search_type || context.route.searchType || '';
  app.selectedKeys = [...(context.workspace?.search_keys || [])];
  app.view = context.workspace?.view || 'table';
  await app.loadNavigation();
  if (app.session !== session) return;
  app.busy = false;
  app.restoringSession = false;
  app.routeReady = true;
  history.replaceState(
    null,
    '',
    windowPageAddress(page.kind, page.project, context.route)
  );
  app.windowPage = { ...page, route: context.route, launch: '' };
  await nextTick();
  await openWindowPageTarget(app, context);
  app.windowPageClosed = false;
}

export function installWindowPages(app) {
  const channels = new Set();
  let alive = true;
  const launch = (event) => {
    const { kind } = event.detail;
    if (!Object.hasOwn(windowPages, kind) || !app.session) return;
    try {
      const spec = windowPages[kind];
      const view = spec.ref ? app.$refs[spec.ref] : null;
      const supplied = event.detail.context;
      const values =
        (typeof supplied === 'function' ? supplied() : supplied) ||
        view?.windowContext?.() ||
        {};
      if (kind === 'sobject_info' && !values.route)
        values.route = { key: app.detail?.__search_key__ };
      if (kind === 'administration') {
        if (app.administrationLocked)
          throw Error('Apply or discard unsaved changes first');
        values.route = { section: app.administrationSection };
      }
      const context = snapshot({
        ...values,
        kind,
        project: values.project ?? app.workspaceProject ?? app.project ?? '',
        user: app.session.login,
        route: values.route || {},
        workspace: app.agentContext()
      });
      structuredClone(context);
      const ownerSession = app.session;
      const id = randomUuid(),
        channel = new BroadcastChannel('tactic-window:' + id);
      const close = () => {
        clearTimeout(timer);
        channel.close();
        channels.delete(close);
      };
      const timer = setTimeout(close, 120000);
      channels.add(close);
      channel.onmessage = (message) => {
        if (message.data?.type === 'ready') {
          if (
            !alive ||
            app.session !== ownerSession ||
            message.data.login !== context.user
          ) {
            channel.postMessage({
              type: 'error',
              message:
                'The window session or project changed. Reopen it from the original window.'
            });
            close();
          } else channel.postMessage({ type: 'context', value: context });
        } else if (message.data?.type === 'accepted') close();
      };
      const url = windowPageAddress(kind, context.project, context.route);
      url.searchParams.set('launch', id);
      window.open(url.href, '_blank', 'noopener');
    } catch (error) {
      notify('error', error.message);
    }
  };
  const closed = (event) => {
    if (app.windowPage?.kind !== event.detail.kind) return;
    app.windowPageClosed = true;
    window.close();
  };
  const sessionChanged = (event) => {
    if (!app.windowPage || event.key !== 'tactic_stream.session') return;
    let saved;
    try {
      saved = JSON.parse(event.newValue);
    } catch {
      saved = null;
    }
    if (
      saved?.ticket === app.session?.ticket &&
      saved?.login === app.session?.login
    )
      return;
    // Unmount old owners without clearing another tab's newly signed-in session.
    app.sessionRequest++;
    app.session = null;
    app.windowPageTool = null;
    app.error = 'Session ended. Sign in again.';
  };
  window.addEventListener('storage', sessionChanged);
  window.addEventListener('tactic-window-page', launch);
  window.addEventListener('tactic-window-page-closed', closed);
  return () => {
    alive = false;
    window.removeEventListener('tactic-window-page', launch);
    window.removeEventListener('tactic-window-page-closed', closed);
    for (const close of [...channels]) close();
    window.removeEventListener('storage', sessionChanged);
  };
}
