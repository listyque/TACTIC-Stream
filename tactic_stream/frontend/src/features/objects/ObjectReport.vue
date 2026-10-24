<script setup>
import { computed, inject, nextTick, ref, watch, onBeforeUnmount } from 'vue';
import { resultItems } from '../../api.js';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import { timestampLabel, timestampFullLabel } from '../activity/activity.js';
import ObjectReportSurface from './ObjectReportSurface.vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { usePagination } from '../../controls/pagination.js';
import AppButton from '../../controls/AppButton.vue';
import ActivityEventCard from '../activity/ActivityEventCard.vue';
import ObjectSnapshotTree from './ObjectSnapshotTree.vue';
import FilePreview from './FilePreview.vue';
import { fileBlob } from './previewFiles.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/report.ui.mjs';
const props = defineProps({ ticket: String, project: String, record: Object });
const emit = defineEmits(['open-link', 'leave']);
const openObjectTab = inject('openObjectTab', null),
  openTaskInspector = inject('openTaskInspector', null),
  openTaskManager = inject('openTaskManager', null),
  openUserProfile = inject('openUserProfile', null);
const openSnapshotBrowser = inject('openSnapshotBrowser', null);
const scroll = ref(null),
  content = ref(null),
  tabs = ref(null),
  preview = ref(null),
  width = ref(0),
  data = ref(null),
  dataPage = ref(''),
  busy = ref(false),
  error = ref(''),
  page = ref('tasks'),
  activity = ref([]);
let generation = 0,
  observer;
const pages = new Map();
const cache = new Map();
const identity = computed(() =>
  JSON.stringify([props.project, props.record?.__search_key__])
);
const snapshotGroups = computed(() =>
  (data.value?.snapshot_processes || []).map((group) => ({
    ...group,
    snapshots: group.snapshots.map((row) => ({
      ...row,
      timestampPretty: timestampLabel(row.timestamp),
      timestampFull: timestampFullLabel(row.timestamp)
    }))
  }))
);
const model = computed(() => {
  const value = data.value || { summary: {}, metrics: {} };
  const now = new Date();
  return {
    ...value,
    page: page.value,
    busy: busy.value,
    summary: {
      ...value.summary,
      updatedPretty: timestampLabel(value.summary.updatedFull, now)
    },
    tasks: (value.tasks || []).map((row) => ({
      ...row,
      endPretty: timestampLabel(row.end, now),
      endFull: timestampFullLabel(row.end)
    })),
    notes: (value.notes || []).map((row) => ({
      ...row,
      timestampPretty: timestampLabel(row.timestamp, now),
      timestampFull: timestampFullLabel(row.timestamp)
    }))
  };
});
const tabScene = computed(() =>
  UI.tabs(page.value, width.value, appearance.language)
);
const pageReady = computed(() => dataPage.value === page.value);
const pagination = usePagination(
  scroll,
  content,
  () =>
    page.value === 'activity' &&
    pageReady.value &&
    data.value?.hasMore &&
    !busy.value &&
    !error.value,
  () => load(true)
);
watch([pageReady, busy, activity], pagination.check, { flush: 'post' });
async function load(append = false, refresh = false) {
  const key = props.record?.__search_key__;
  if (!key || !props.ticket || !props.project) return;
  const request = ++generation;
  const cacheKey = JSON.stringify([identity.value, page.value]);
  if (!append && !refresh && cache.has(cacheKey)) {
    data.value = cache.get(cacheKey);
    dataPage.value = page.value;
    activity.value = data.value.activity;
    error.value = '';
    busy.value = false;
    return;
  }
  busy.value = true;
  error.value = '';
  try {
    const result = await resultItems(
      props.ticket,
      props.project,
      key.split('?')[0],
      [key],
      {
        branch: { kind: 'object_report', path: page.value },
        offset: append ? activity.value.length : 0,
        limit: 50
      }
    );
    if (request !== generation) return;
    data.value = result;
    dataPage.value = page.value;
    activity.value = append
      ? [...activity.value, ...result.activity]
      : result.activity;
    cache.set(cacheKey, { ...result, activity: activity.value });
    if (cache.size > 1000) cache.delete(cache.keys().next().value);
  } catch (reason) {
    if (request === generation) error.value = reason.message;
  } finally {
    if (request === generation) busy.value = false;
  }
}
function selectPage(value) {
  if (!UI.sections.some((row) => row.value === value) || value === page.value)
    return;
  page.value = value;
  pages.set(identity.value, value);
  activity.value = [];
  scroll.value.scrollTop = 0;
  load();
  pagination.reset();
}
function open(key) {
  if (key) {
    emit('leave');
    openObjectTab?.(
      key.startsWith('skey://') ? key : 'skey://' + key,
      props.project
    );
  }
}
function snapshot(key) {
  const row = data.value.snapshots.find((row) => row.searchKey === key);
  if (row) {
    emit('leave');
    openSnapshotBrowser?.(props.record, row.process, props.project);
  }
}
function file(record) {
  const file = { ...record, code: record.token, filename: record.title };
  preview.value.open(
    { name: record.title, __search_key__: record.searchKey },
    { files: [file], loadFile: fileBlob }
  );
}
async function inspector(process, taskKey = '', noteKey = '') {
  emit('leave');
  return openTaskInspector?.(props.record, {}, process, taskKey, {
    ticket: props.ticket,
    project: props.project,
    searchType: props.record.__search_key__.split('?')[0],
    noteKey
  });
}
async function activityAction(record) {
  emit('leave');
  if (
    record.taskCode &&
    (['status', 'task', 'work_hour'].includes(record.kind) ||
      record.itemType === 'sthpw/task')
  ) {
    const key =
      'sthpw/task?project=' +
      encodeURIComponent(props.project) +
      '&code=' +
      encodeURIComponent(record.taskCode);
    if ((await inspector(record.process, key)) !== false)
      openTaskManager?.(props.record, '', {}, key);
  } else if (record.kind === 'note')
    inspector(
      record.process,
      record.taskCode
        ? 'sthpw/task?project=' +
            encodeURIComponent(props.project) +
            '&code=' +
            encodeURIComponent(record.taskCode)
        : '',
      record.searchKey
    );
  else if (['publication', 'snapshot'].includes(record.kind))
    openSnapshotBrowser?.(props.record, record.process, props.project);
  else open(record.searchKey || props.record.__search_key__);
}
async function action(event) {
  if (event.type === 'page') selectPage(event.value);
  else if (event.type === 'refresh') load(false, true);
  else if (event.type === 'open') open(model.value.summary.searchKey);
  else if (event.type === 'link') {
    emit('leave');
    openObjectTab?.(event.value, props.project);
  } else if (event.type === 'child') open(event.key);
  else if (event.type === 'person') {
    emit('leave');
    openUserProfile?.(event.key);
  } else if (event.type === 'task') {
    if ((await inspector(event.process, event.key)) !== false)
      openTaskManager?.(props.record, '', {}, event.key);
  } else if (event.type === 'note') {
    const row = data.value.notes[event.index];
    await inspector(
      row.process,
      row.isTaskNote
        ? 'sthpw/task?project=' +
            encodeURIComponent(props.project) +
            '&code=' +
            encodeURIComponent(row.taskCode)
        : '',
      row.searchKey
    );
  } else if (event.type === 'filter') {
    emit('leave');
    openTaskManager?.(
      props.record,
      event.field === 'process' ? event.value : '',
      { [event.field]: event.value }
    );
  }
}

watch(
  () => [props.ticket, props.project, props.record],
  async () => {
    generation++;
    data.value = null;
    dataPage.value = '';
    activity.value = [];
    error.value = '';
    busy.value = false;
    page.value = pages.get(identity.value) || 'tasks';
    if (pages.size > 200) pages.delete(pages.keys().next().value);
    await nextTick();
    if (tabs.value && !observer) {
      observer = observeFrameSizes(() => {
        width.value = tabs.value.clientWidth;
      });
      observer.observe(tabs.value);
      width.value = tabs.value.clientWidth;
    }
    load(false, true);
  },
  { immediate: true }
);
watch(
  () => props.ticket,
  () => {
    pages.clear();
    cache.clear();
  }
);
onBeforeUnmount(() => {
  generation++;
  observer?.disconnect();
});
</script>
<template>
  <div ref="scroll" class="object-report" :aria-busy="busy" tabindex="0">
    <div ref="content" class="object-report-content">
      <ObjectReportSurface v-if="data" :model="model" @event="action" />
      <div ref="tabs" class="object-report-tabs">
        <FrameView :scene="tabScene" @event="action" />
      </div>
      <p v-if="error" class="error" role="alert">
        {{ t(error) }}
        <AppButton label="Retry" :disabled="busy" @click="load(false, true)" />
      </p>
      <p v-if="busy && !pageReady" role="status">{{ t('Loading data…') }}</p>
      <ObjectReportSurface
        v-if="pageReady && ['tasks', 'notes', 'children'].includes(page)"
        :model="model"
        part="page"
        @event="action"
      />
      <ObjectSnapshotTree
        v-else-if="pageReady && page === 'snapshots'"
        :key="identity"
        :metrics="data.metrics"
        :groups="snapshotGroups"
        @snapshot="snapshot"
        @file="file"
      />
      <section
        v-else-if="pageReady && page === 'activity'"
        class="object-report-activity"
      >
        <ActivityEventCard
          v-for="(record, index) in activity"
          :key="record.eventId || index"
          :record="record"
          @target="open(record.targetSearchKey)"
          @activity="activityAction(record)"
          @open-link="open"
        />
        <p v-if="!activity.length && !busy" class="muted">
          {{ t('No recent activity') }}
        </p>
        <AppButton
          v-if="data.hasMore"
          label="Load more"
          :disabled="busy"
          @click="load(true)"
        />
      </section>
      <FilePreview
        ref="preview"
        :ticket="ticket"
        :project="project"
        :search-type="record?.__search_key__?.split('?')[0]"
      />
    </div>
  </div>
</template>
<style>
.object-details[open] {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 320px;
  width: 76vw;
  height: 80dvh;
  padding: 0;
  background: var(--surface-deep);
}
.object-details > header {
  padding: 6px 12px;
  margin: 0;
  flex: none;
}
.object-details > header small {
  display: none;
}
.object-details > .object-report {
  flex: 1;
  min-height: 0;
}
.object-report {
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 12px 10px 12px 12px;
  background: var(--surface-deep);
  min-width: 0;
}
.object-report-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}
.object-report-tabs {
  height: 36px;
  flex: none;
  min-width: 0;
}
.object-report-activity {
  display: grid;
  gap: 5px;
}
</style>
