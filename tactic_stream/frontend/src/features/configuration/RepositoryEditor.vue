<script setup>
// RepositoryEditorView.qml: 220px catalogue, selected repository, native Config draft owner.
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/configuration/repository.ui.mjs';
const props = defineProps({
  server: Object,
  repositories: Array,
  draft: Object,
  busy: Boolean,
  dirty: Boolean
});
const emit = defineEmits(['check', 'close', 'save', 'reset']);
const selected = ref('default');
const entries = computed(() => {
  try {
    return [
      ...new Set([
        ...Object.keys(mapping('asset_base_dir')),
        ...Object.keys(mapping('base_dir_alias')),
        'plugins'
      ])
    ].map((alias) => ({
      ...(props.repositories?.find((item) => item.alias === alias) || {}),
      alias,
      path: root(alias)
    }));
  } catch {
    return props.repositories || [];
  }
});
const record = computed(
  () =>
    entries.value.find((item) => item.alias === selected.value) ||
    entries.value[0]
);
function stored(key) {
  return props.server?.draft['checkin/' + key] ?? '';
}
function mapping(key) {
  const raw = stored(key);
  return !raw ? {} : raw.startsWith('{') ? JSON.parse(raw) : { default: raw };
}
const invalid = computed(() => {
  try {
    for (const key of [
      'asset_base_dir',
      'base_dir_alias',
      'web_base_dir',
      'repository_display',
      'win32_client_repo_dir',
      'linux_client_repo_dir'
    ])
      mapping(key);
    return false;
  } catch {
    return true;
  }
});
function presentation(item) {
  try {
    return mapping('repository_display')[item.alias] || {};
  } catch {
    return {};
  }
}
function title(item) {
  return presentation(item).title || item.title;
}
function update(key, field, value) {
  if (!record.value || invalid.value) return;
  const entries = Object.assign(Object.create(null), mapping(key)),
    alias = record.value.alias;
  if (field) entries[alias] = { ...entries[alias], [field]: value };
  else if (value.trim() || ['asset_base_dir', 'base_dir_alias'].includes(key))
    entries[alias] = value;
  else delete entries[alias];
  props.server.editSetting(
    'checkin/' + key,
    Object.keys(entries).length ? JSON.stringify(entries) : ''
  );
}
function path(key) {
  try {
    return mapping(key)[record.value?.alias] || '';
  } catch {
    return '';
  }
}
function color() {
  const value = presentation(record.value).color;
  return Array.isArray(value)
    ? '#' +
        value.map((channel) => channel.toString(16).padStart(2, '0')).join('')
    : value
      ? '#' + value.replace(/^#/, '')
      : '';
}
function root(alias) {
  try {
    return (
      mapping('base_dir_alias')[alias] ||
      mapping('asset_base_dir')[alias] ||
      props.repositories?.find((item) => item.alias === alias)?.path ||
      ''
    );
  } catch {
    return props.repositories?.find((item) => item.alias === alias)?.path || '';
  }
}
function enabled(alias) {
  return (
    alias !== 'plugins' &&
    (props.draft.enabledAliases === null ||
      props.draft.enabledAliases.includes(alias))
  );
}
function enable(alias, value) {
  props.draft.enabledAliases = entries.value
    .filter(
      (item) =>
        item.alias !== 'plugins' &&
        (item.alias === alias ? value : enabled(item.alias))
    )
    .map((item) => item.alias);
  if (!enabled(props.draft.defaultAlias))
    props.draft.defaultAlias = props.draft.enabledAliases[0] || '';
}
function add() {
  let index = 0;
  while (entries.value.some((item) => item.alias === 'custom_' + index))
    index++;
  const alias = 'custom_' + index;
  selected.value = alias;
  const roots = Object.assign(Object.create(null), mapping('asset_base_dir'));
  roots[alias] = '';
  props.server.editSetting('checkin/asset_base_dir', JSON.stringify(roots));
  const urls = Object.assign(Object.create(null), mapping('web_base_dir'));
  urls[alias] = '/repository/' + alias;
  props.server.editSetting('checkin/web_base_dir', JSON.stringify(urls));
  props.draft.enabledAliases = entries.value
    .filter((item) => item.alias !== alias && enabled(item.alias))
    .map((item) => item.alias);
}
function remove() {
  const alias = record.value.alias;
  for (const key of [
    'asset_base_dir',
    'base_dir_alias',
    'web_base_dir',
    'repository_display',
    'win32_client_repo_dir',
    'linux_client_repo_dir'
  ]) {
    const values = Object.assign(Object.create(null), mapping(key));
    delete values[alias];
    props.server.editSetting(
      'checkin/' + key,
      Object.keys(values).length ? JSON.stringify(values) : ''
    );
  }
  if (props.draft.enabledAliases)
    props.draft.enabledAliases = props.draft.enabledAliases.filter(
      (item) => item !== alias
    );
  if (props.draft.defaultAlias === alias)
    props.draft.defaultAlias =
      entries.value.find((item) => enabled(item.alias))?.alias || '';
}
const host = ref(null),
  viewport = ref({ width: 1000, height: 700 }),
  editing = ref(false),
  advanced = ref(false);
const canonical = computed(() =>
  entries.value.map((item) => ({
    ...item,
    code: item.alias,
    title: title(item) || item.alias,
    active: enabled(item.alias),
    isDefault: props.draft.defaultAlias === item.alias,
    defaultEligible: item.alias !== 'plugins',
    custom: item.alias.startsWith('custom_')
  }))
);
const model = computed(() => ({
  selected: record.value?.alias,
  record: record.value
    ? {
        ...canonical.value.find((item) => item.alias === record.value.alias),
        title:
          presentation(record.value).title ||
          title(record.value) ||
          record.value.alias,
        serverPath: root(record.value.alias),
        webPath: path('web_base_dir'),
        windowsPath: path('win32_client_repo_dir'),
        linuxPath: path('linux_client_repo_dir'),
        color: color(),
        statusText: t(
          record.value.status === 'available'
            ? 'Available'
            : record.value.status === 'inaccessible'
              ? 'Folder not found or inaccessible'
              : 'Not checked'
        )
      }
    : {},
  dirty: props.dirty,
  busy: props.busy,
  editable: !invalid.value,
  notice: props.server?.notice,
  error:
    props.server?.error ||
    (invalid.value
      ? t(
          'Fix the repository JSON in Advanced settings before editing these fields.'
        )
      : ''),
  editing: editing.value,
  style: appearance.theme
}));
const scene = computed(() =>
  UI.editor(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const row = (list, record) => UI.row(model.value, record, list.width - 16);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function dispatch(action) {
  if (action.type === 'select') {
    selected.value = action.alias;
    editing.value = true;
  } else if (action.type === 'back') editing.value = false;
  else if (action.type === 'add') {
    add();
    editing.value = true;
  } else if (action.type === 'remove') remove();
  else if (action.type === 'advanced') advanced.value = !advanced.value;
  else if (action.type === 'check')
    emit(
      'check',
      Object.fromEntries(
        entries.value
          .filter((item) => item.alias !== 'plugins')
          .map((item) => [item.alias, root(item.alias)])
      )
    );
  else if (action.type === 'field') {
    if (action.field === 'active') enable(record.value.alias, action.value);
    else if (action.field === 'isDefault')
      props.draft.defaultAlias = action.value
        ? record.value.alias
        : entries.value.find(
            (item) => item.alias !== record.value.alias && enabled(item.alias)
          )?.alias || record.value.alias;
    else if (action.field === 'title' || action.field === 'color')
      update('repository_display', action.field, action.value);
    else
      update(
        {
          serverPath: Object.hasOwn(
            mapping('base_dir_alias'),
            record.value.alias
          )
            ? 'base_dir_alias'
            : 'asset_base_dir',
          webPath: 'web_base_dir',
          windowsPath: 'win32_client_repo_dir',
          linuxPath: 'linux_client_repo_dir'
        }[action.field],
        null,
        action.value
      );
  } else if (
    action.type === 'close' ||
    action.type === 'save' ||
    action.type === 'reset'
  )
    emit(action.type);
}
</script>
<template>
  <div class="repository-editor-frame-shell">
    <div ref="host" class="repository-editor-frame">
      <FrameView
        :scene="scene"
        :models="{ repositories: canonical }"
        :describe-row="row"
        @event="dispatch"
      />
    </div>
    <section v-show="advanced" class="repository-editor-advanced-frame">
      <slot />
    </section>
  </div>
</template>
<style>
.repository-editor-frame-shell {
  height: 100%;
  width: 100%;
  min-height: 0;
  overflow: auto;
}
.repository-editor-frame {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 480px;
}
.repository-editor-frame > .frame-view {
  position: absolute;
  inset: 0;
}
.repository-editor-advanced-frame {
  padding: 16px;
}
</style>
