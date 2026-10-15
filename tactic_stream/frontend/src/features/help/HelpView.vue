<script setup>
import {
  computed,
  markRaw,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch
} from 'vue';
import FrameView from '../../frame/FrameView.vue';
import DocumentPane from '../../controls/DocumentPane.vue';
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { downloadBlob } from '../../controls/files.js';
import { t } from '../../i18n.js';
import { loadArticles } from './help.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/support/help/help.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/support/help/help.state.mjs';

const props = defineProps({
  label: { type: String, default: 'Help' },
  topic: { type: String, default: '' }
});
const dialog = ref(null),
  layout = ref(null),
  frame = ref(null),
  documentView = ref(null);
const viewport = ref({ width: 900, height: 650 });
const ui = ref(State.initial()),
  articles = ref([]),
  busy = ref(false),
  error = ref('');
const opened = ref(false);
const selected = computed(() => ui.value.selected),
  query = computed(() => ui.value.query),
  topicsVisible = computed(() => ui.value.topicsVisible);
const current = computed(() =>
  articles.value.find((row) => row.id === selected.value)
);
const data = computed(() => ({
  articles: articles.value,
  busy: busy.value,
  canDownload: true,
  fileLinks: true,
  style: appearance.theme
}));
const scene = computed(() =>
  UI.describe(
    {
      selected: selected.value,
      query: query.value,
      topicsVisible: topicsVisible.value
    },
    data.value,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const models = computed(() => ({ helpTopics: scene.value.topicRows }));
const documentComponent = markRaw(DocumentPane);
const busyComponent = markRaw(BusyIndicator);
const captureDocument = (value) => {
  documentView.value = value;
};
const views = computed(() => ({
  busy: { component: busyComponent, props: { running: busy.value } },
  document: {
    component: documentComponent,
    captureRef: captureDocument,
    props: {
      documentKey: selected.value,
      text: current.value?.body || '',
      summary: current.value?.summary || '',
      notice: current.value?.reference
        ? t(
            'Original Handler reference. Desktop-specific options belong to Handler; this article does not indicate that every feature has been migrated to Stream.'
          )
        : '',
      error: error.value,
      scrollOffset: State.offset(ui.value, selected.value),
      presented: opened.value && (!scene.value.compact || !topicsVisible.value),
      onScroll: (value) => dispatch({ type: 'scroll', ...value }),
      onLink: (id) => dispatch({ type: 'select', id })
    }
  }
}));
let controller = null,
  generation = 0,
  openRequest = 0,
  loadedLanguage = '',
  observer;
function row(list, record) {
  return UI.topicRow(
    { selected: selected.value },
    record,
    list.width - 16,
    appearance.language
  );
}
async function reveal(id) {
  await nextTick();
  const list = dialog.value?.querySelector('[data-frame="helpTopicList"]');
  const index = scene.value.topicRows.findIndex((row) => row.id === id);
  if (!list || index < 0) return;
  list.scrollTop = State.revealOffset(
    list.scrollTop,
    index,
    list.clientHeight,
    scene.value.topicRows.length
  );
  list.dispatchEvent(new Event('scroll'));
}
async function dispatch(action) {
  if (['select', 'open', 'close'].includes(action.type))
    documentView.value?.capture();
  const result = State.transition(ui.value, articles.value, action);
  ui.value = result.model;
  for (const command of result.commands) {
    if (command.type === 'reload') reload();
    else if (command.type === 'close') close();
    // The native anchor preserves middle-click, copy-link and browser popup ownership.
    else if (command.type === 'openFile') continue;
    else if (command.type === 'download' && current.value)
      downloadBlob(
        new Blob([current.value.source], {
          type: 'text/markdown;charset=utf-8'
        }),
        current.value.file.split('/').at(-1)
      );
    else if (command.type === 'reveal') await reveal(command.id);
    else if (command.type === 'focusArticle') {
      await nextTick();
      documentView.value?.focus();
    } else if (command.type === 'focusTopic') {
      await reveal(command.id);
      frame.value?.focusControl('helpTopic_' + command.id);
    }
  }
}
async function reload() {
  controller?.abort();
  controller = new AbortController();
  const request = ++generation;
  const language = appearance.language;
  busy.value = true;
  error.value = '';
  try {
    const loaded = await loadArticles(language, controller.signal);
    if (request !== generation) return;
    articles.value = loaded;
    loadedLanguage = language;
    dispatch({ type: 'loaded' });
  } catch (exception) {
    if (request === generation && exception.name !== 'AbortError')
      error.value = exception.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
async function open(id = props.topic) {
  const request = ++openRequest;
  if (!dialog.value.open) dialog.value.show();
  opened.value = true;
  if (!articles.value.length || loadedLanguage !== appearance.language)
    await reload();
  if (request !== openRequest || !opened.value) return;
  await dispatch({ type: 'open', id });
  if (request === openRequest && opened.value)
    await documentView.value?.restore();
}
function closed() {
  if (dialog.value?.open) return;
  openRequest++;
  generation++;
  controller?.abort();
  busy.value = false;
  opened.value = false;
}
function close() {
  documentView.value?.capture();
  openRequest++;
  generation++;
  controller?.abort();
  busy.value = false;
  opened.value = false;
  dialog.value?.close();
}
watch(
  () => appearance.language,
  () => {
    if (opened.value) reload();
  }
);
watch(viewport, () => {
  if (opened.value) reveal(selected.value);
});
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const entry = entries.find((entry) => entry.target === layout.value);
    if (entry?.contentRect.width && entry.contentRect.height)
      viewport.value = {
        width: entry.contentRect.width,
        height: entry.contentRect.height
      };
  });
  observer.observe(layout.value);
});
onBeforeUnmount(() => {
  generation++;
  controller?.abort();
  observer?.disconnect();
  dialog.value?.close();
});
defineExpose({ open, close });
</script>
<template>
  <Teleport to="body">
    <dialog
      v-window="{ kind: 'help', type: 'window' }"
      ref="dialog"
      class="help-view"
      :aria-label="t(label)"
      @cancel.prevent="close"
      @close="closed"
    >
      <header class="help-window-header">
        <AppIcon name="help" /><strong>{{ t(label) }}</strong
        ><AppButton icon-only label="Close help" icon="close" @click="close" />
      </header>
      <div ref="layout" class="help-layout">
        <FrameView
          ref="frame"
          :scene="scene"
          :models="models"
          :views="views"
          :describe-row="row"
          @event="dispatch"
        />
      </div>
    </dialog>
  </Teleport>
</template>
<style>
.help-view {
  width: min(70dvw, calc(100dvw - 16px));
  height: min(76dvh, calc(100dvh - 16px));
  min-width: min(720px, calc(100dvw - 16px));
  max-width: none;
  max-height: none;
  padding: 0;
  margin: auto;
  background: var(--page);
  color: var(--on-surface);
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  overflow: hidden;
}
.help-view[open] {
  display: flex;
  flex-direction: column;
}
.help-window-header {
  height: 40px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 2px 6px 2px 14px;
  border-bottom: 1px solid var(--outline-variant);
  background: var(--surface);
}
.help-window-header > strong {
  flex: 1;
}
.help-window-header > .app-icon {
  color: var(--primary);
}
.help-layout {
  flex: 1;
  min-height: 0;
  min-width: 0;
  position: relative;
}
</style>
