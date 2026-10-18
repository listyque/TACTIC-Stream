<script setup>
// Handler MatchingTemplatesView.qml / MatchingTemplatesController (EPL-1.0).
import { computed, onMounted, onBeforeUnmount, nextTick, ref } from 'vue';
import { rpc } from '../../api.js';
import { t } from '../../i18n.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import { randomId } from '../../controls/identity.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/files/matching.ui.mjs';
const props = defineProps({
  scope: Object,
  items: Array,
  padding: Number,
  processes: Array,
  context: String
});
const emit = defineEmits(['save', 'close']);
const rows = ref(props.items.map((row) => ({ ...row }))),
  selectedIndex = ref(0),
  paneWidth = ref(0),
  editing = ref(false),
  viewport = ref({ width: 860, height: 620 }),
  example = ref(''),
  result = ref(''),
  matchedType = ref(''),
  error = ref(''),
  busy = ref(false);
const selected = computed(() => rows.value[selectedIndex.value]);
const workspace = ref(null),
  presenter = ref(null),
  menu = ref(null),
  menuAnchor = ref(null);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    viewport.value = { width: box.width, height: box.height };
  });
  observer.observe(workspace.value);
});
onBeforeUnmount(() => {
  request++;
  observer?.disconnect();
});
const initialPadding = props.padding;
const dirty = computed(
  () =>
    props.padding !== initialPadding ||
    JSON.stringify(
      rows.value.map(
        ({ preview, matchingType, validationError, ...row }) => row
      )
    ) !==
      JSON.stringify(
        props.items.map(
          ({ preview, matchingType, validationError, ...row }) => row
        )
      )
);
let request = 0;
async function inspect(test = false) {
  if (test && !selected.value) return false;
  const id = ++request;
  error.value = '';
  result.value = '';
  busy.value = true;
  try {
    const patterns = test
      ? [selected.value.pattern]
      : rows.value.map((row) => row.pattern);
    const response = (
      await rpc(
        'execute_cmd',
        [
          props.scope,
          'tactic.command.browser_checkin_cmd.BrowserCheckinCmd',
          {
            action: 'templates',
            templates: patterns,
            padding: props.padding,
            example: test ? example.value.trim() : ''
          }
        ],
        {},
        true
      )
    ).info.templates;
    if (id !== request) return false;
    for (const row of rows.value) {
      const value = response.find((item) => item.pattern === row.pattern);
      if (value) {
        row.preview = value.preview;
        row.matchingType = value.matchingType;
        row.validationError = value.validationError;
      }
    }
    error.value = test
      ? response[0].validationError
      : rows.value.find((row) => row.enabled && row.validationError)
          ?.validationError || '';
    if (test) {
      matchedType.value = response[0].matched;
      result.value = !example.value.trim()
        ? 'Enter a filename to test'
        : matchedType.value
          ? 'Matched as {type}'
          : 'No match';
    }
    return !error.value;
  } catch (failure) {
    if (id === request) error.value = failure.message;
    return false;
  } finally {
    if (id === request) busy.value = false;
  }
}
function select(index) {
  selectedIndex.value = index;
  editing.value = true;
  result.value = '';
  error.value = '';
}
function create(duplicate = false) {
  const item = duplicate
    ? { ...selected.value, locked: false }
    : {
        enabled: true,
        pattern: '$FILENAME.$EXT',
        process: '',
        context: '',
        locked: false
      };
  const index = duplicate ? selectedIndex.value + 1 : rows.value.length;
  item.templateId = randomId();
  rows.value.splice(index, 0, item);
  select(index);
  inspect();
}
function move(offset) {
  const index = selectedIndex.value,
    target = index + offset;
  if (target < 0 || target >= rows.value.length) return;
  rows.value.splice(target, 0, ...rows.value.splice(index, 1));
  select(target);
}
function remove() {
  if (!selected.value || selected.value.locked) return;
  rows.value.splice(selectedIndex.value, 1);
  select(Math.min(selectedIndex.value, rows.value.length - 1));
}
async function save() {
  if (await inspect())
    emit(
      'save',
      rows.value.map(
        ({ preview, matchingType, matched, validationError, ...row }) => row
      )
    );
}
function close() {
  if (!dirty.value || window.confirm(t('Discard unsaved changes?')))
    emit('close');
}
defineExpose({ close });
inspect();

const model = computed(() => ({
  selected: selectedIndex.value,
  record: selected.value || {},
  count: rows.value.length,
  busy: busy.value,
  canAdd: rows.value.length < 32,
  dirty: dirty.value,
  example: example.value,
  result: UI.testResult(result.value, appearance.language, matchedType.value),
  error: t(error.value),
  processes: props.processes || [],
  contexts: props.context ? [props.context] : [],
  editing: editing.value,
  paneWidth: paneWidth.value
}));
const presentedRows = computed(() =>
  rows.value.map((row, index) => ({
    ...row,
    templateId: row.templateId || String(index),
    templateEnabled: row.enabled,
    selected: index === selectedIndex.value,
    priority: index
  }))
);
const scene = computed(() =>
  UI.describe(
    model.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const describeRow = (list, record) =>
  UI.row(model.value, record, list.width - 16, appearance.language);
function dispatch(action, source) {
  if (action.type === 'select') {
    selectedIndex.value = action.index;
    result.value = error.value = '';
    if (action.focus) {
      const key = presentedRows.value[action.index].templateId;
      nextTick(() =>
        presenter.value.focusListRow(
          'matchingTemplatesList',
          action.index,
          'matchingTemplateSelect_' + key
        )
      );
    } else editing.value = true;
  } else if (action.type === 'enabled') {
    selectedIndex.value = action.index;
    selected.value.enabled = action.value;
    inspect();
  } else if (action.type === 'field') {
    if (selected.value && !selected.value.locked)
      selected.value[action.field] = action.value;
  } else if (action.type === 'validate') inspect();
  else if (action.type === 'example') example.value = action.value;
  else if (action.type === 'test') inspect(true);
  else if (action.type === 'create') create();
  else if (action.type === 'duplicate') create(true);
  else if (action.type === 'move_up') move(-1);
  else if (action.type === 'move_down') move(1);
  else if (action.type === 'delete') remove();
  else if (action.type === 'save') save();
  else if (action.type === 'close') close();
  else if (action.type === 'splitter') paneWidth.value = action.value;
  else if (action.type === 'back') editing.value = false;
  else if (action.type === 'menu') {
    menuAnchor.value = source;
    if (menu.value.open) menu.value.close(true);
    else menu.value.openAt({ target: source });
  }
}
</script>
<template>
  <div ref="workspace" class="matching-templates-workspace" :aria-busy="busy">
    <FrameView
      ref="presenter"
      :scene="scene"
      :models="{ templates: presentedRows }"
      :describe-row="describeRow"
      @event="dispatch"
    />
    <AppMenu
      ref="menu"
      external-trigger
      overlay
      :anchor="menuAnchor"
      label="Template actions"
    >
      <AppButton
        v-for="action in UI.actions(model)"
        :key="action.command"
        :label="action.title"
        :icon="action.icon"
        :disabled="!action.enabled"
        @click="dispatch({ type: action.command })"
      />
    </AppMenu>
  </div>
</template>
<style>
.matching-templates-workspace {
  position: relative;
  flex: 1;
  min-height: 0;
  min-width: 0;
  background: var(--surface-deep);
}
</style>
