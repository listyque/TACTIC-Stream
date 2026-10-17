<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { searchConfiguration } from '../../api.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { virtualRange } from '../../../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/visibility.ui.mjs';
import AppButton from '../../controls/AppButton.vue';

const props = defineProps({
  ticket: String,
  project: String,
  searchType: String,
  workspaceId: String,
  ignore: Object
});
const emit = defineEmits(['apply']);
const dialog = ref(null),
  body = ref(null),
  viewport = ref(null),
  width = ref(440),
  treeWidth = ref(400),
  treeHeight = ref(200),
  top = ref(0),
  title = ref(''),
  records = ref([]),
  baseline = ref('{}'),
  busy = ref(false),
  error = ref(''),
  valid = ref(false),
  togglers = ref(false);
const header = computed(() =>
  UI.header({ title: title.value }, width.value, appearance.language)
);
const footer = computed(() =>
  UI.footer(
    {
      valid: valid.value,
      dirty: JSON.stringify(UI.ignoreFrom(records.value)) !== baseline.value
    },
    width.value,
    appearance.language
  )
);
const togglerScene = computed(() =>
  UI.togglers(
    { expanded: togglers.value },
    width.value - 8,
    appearance.language
  )
);
const visible = computed(() =>
  records.value
    .map((row, index) => ({ ...row, sourceIndex: index }))
    .filter((row) => row.rowVisible)
);
const range = computed(() =>
  virtualRange(
    visible.value.length,
    UI.rowHeight,
    treeHeight.value,
    top.value,
    3
  )
);
const cells = computed(() =>
  visible.value
    .slice(range.value.first, range.value.last)
    .map((row, index) => ({
      row,
      top: (range.value.first + index) * UI.rowHeight
    }))
);
const empty = computed(() =>
  UI.empty(
    'Select a Search Tab first',
    treeWidth.value,
    treeHeight.value,
    appearance.language
  )
);
let generation = 0,
  observer,
  inputModifiers = {};
watch(
  () => [props.ticket, props.project, props.searchType, props.workspaceId],
  () => {
    generation++;
    busy.value = false;
    valid.value = false;
    if (dialog.value?.open)
      error.value = 'Search context changed. Reopen the editor.';
  }
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    for (const entry of entries) {
      if (entry.target === body.value) width.value = entry.contentRect.width;
      else {
        treeWidth.value = entry.target.clientWidth - 4;
        treeHeight.value = entry.contentRect.height;
      }
    }
  });
  observer.observe(body.value);
  observer.observe(viewport.value);
});
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
async function open() {
  if (dialog.value.open) return;
  dialog.value.showModal();
  await load();
}
async function load() {
  const request = ++generation,
    context = {
      ticket: props.ticket,
      project: props.project,
      type: props.searchType
    };
  busy.value = true;
  valid.value = false;
  error.value = '';
  records.value = [];
  try {
    const result = await searchConfiguration(
      'visibility',
      context.ticket,
      context.project,
      context.type
    );
    if (request !== generation) return;
    title.value = result.title;
    records.value = UI.applyIgnore(result.records, props.ignore || {});
    baseline.value = JSON.stringify(UI.ignoreFrom(records.value));
    valid.value = !!records.value.length;
  } catch (failure) {
    if (request === generation) error.value = failure.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
function cancel() {
  generation++;
  busy.value = false;
  dialog.value.close();
}
function command(action) {
  if (action.type === 'cancel') {
    cancel();
    return;
  }
  if (!valid.value) return;
  if (action.type === 'save' || action.type === 'saveClose') {
    const ignore = UI.ignoreFrom(records.value);
    emit('apply', ignore);
    baseline.value = JSON.stringify(ignore);
    if (action.type === 'saveClose') dialog.value.close();
  } else if (action.type === 'togglers') togglers.value = !togglers.value;
  else UI.change(records.value, action);
}
function rowEvent(action) {
  command({ ...action, ...inputModifiers });
  inputModifiers = {};
}
function capture(event) {
  inputModifiers = {
    control: event.ctrlKey || event.metaKey,
    shift: event.shiftKey
  };
}
defineExpose({ open });
</script>
<template>
  <dialog
    ref="dialog"
    v-window="{ kind: 'process_filter_editor' }"
    class="configuration-dialog process-visibility-dialog"
    :aria-label="t('Filter Processes')"
    @cancel.prevent="cancel"
  >
    <header>
      <strong>{{ t('Filter Processes') }}</strong
      ><AppButton label="Close" icon="close" icon-only @click="cancel" />
    </header>
    <section ref="body" class="process-visibility-body" :aria-busy="busy">
      <FrameView :scene="header" style="height: 42px; flex: none" />
      <p v-if="busy" role="status">{{ t('Loading data…') }}</p>
      <p v-if="error" class="error" role="alert">
        {{ t(error) }} <AppButton label="Retry" @click="load" />
      </p>
      <div class="process-visibility-tree">
        <div
          ref="viewport"
          class="process-visibility-viewport"
          @scroll.passive="top = $event.target.scrollTop"
          role="tree"
          :aria-label="t('Filter Processes')"
        >
          <div :style="{ position: 'relative', height: range.height + 'px' }">
            <div
              v-for="cell in cells"
              :key="cell.row.nodeId"
              :data-process-id="cell.row.nodeId"
              :style="{
                position: 'absolute',
                top: cell.top + 'px',
                width: treeWidth + 'px',
                height: UI.rowHeight + 'px'
              }"
              @pointerdown.capture="capture"
              @keydown.capture="capture"
            >
              <FrameView
                :scene="
                  UI.row(
                    cell.row,
                    cell.row.sourceIndex,
                    treeWidth,
                    appearance.language
                  )
                "
                @event="rowEvent"
              />
            </div>
          </div>
          <FrameView v-if="!records.length && !busy && !error" :scene="empty" />
        </div>
        <FrameView
          :scene="togglerScene"
          :style="{
            height: togglerScene.contentHeight + 'px',
            flex: 'none',
            margin: '4px',
            width: 'calc(100% - 8px)'
          }"
          @event="command"
        />
      </div>
      <FrameView
        :scene="footer"
        :style="{ height: footer.contentHeight + 'px', flex: 'none' }"
        @event="command"
      />
    </section>
  </dialog>
</template>
<style>
.process-visibility-dialog {
  width: 440px;
  height: 440px;
  padding: 0;
  overflow: hidden;
}
.process-visibility-dialog > header {
  height: 44px;
  padding: 6px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.process-visibility-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  height: calc(100% - 44px);
  min-height: 0;
}
.process-visibility-tree {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--outline-variant);
  border-radius: var(--item-radius);
  background: var(--surface);
  overflow: hidden;
}
.process-visibility-viewport {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  scrollbar-gutter: stable;
  margin: 4px;
}
</style>
