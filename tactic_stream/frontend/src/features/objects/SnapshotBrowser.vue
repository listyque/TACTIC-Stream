<script setup>
// Handler SnapshotBrowser.qml, SnapshotStateMixin and SnapshotActionsMixin (EPL-1.0).
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import { resultItems } from '../../api.js';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import { copyImage, copyText } from '../../controls/clipboard.js';
import { notify } from '../activity/notifications.js';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppIcon from '../../controls/AppIcon.vue';
import SnapshotToolbar from './SnapshotToolbar.vue';
import ActionRows from '../../controls/ActionRows.vue';
import * as SnapshotUI from '../../../../src/tactic_stream/shared_ui/features/objects/snapshot.ui.mjs';
import AppSlider from '../../controls/AppSlider.vue';
import MiddleElide from '../../controls/MiddleElide.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import FilePreview from './FilePreview.vue';
import { fileBlob as blob } from './previewFiles.js';
import RecordForm from './RecordForm.vue';
import ObjectAction from './ObjectAction.vue';

const props = defineProps({
  ticket: String,
  project: String,
  target: Object,
  active: Boolean
});
const emit = defineEmits(['session-expired', 'changed']);
const defaults = {
  contentMode: 'both',
  imageMode: 'fit',
  orientation: 'horizontal',
  showAll: false,
  showMore: false,
  splitterRatio: 0.52
};
const options = ref({ ...defaults }),
  error = ref(''),
  loading = ref(false),
  loaded = ref(false);
try {
  const saved = JSON.parse(
    localStorage.getItem('tactic_stream.snapshot-browser') || '{}'
  );
  for (const [name, values] of Object.entries({
    contentMode: ['both', 'preview', 'files'],
    imageMode: ['fit', 'fill'],
    orientation: ['horizontal', 'vertical']
  }))
    if (values.includes(saved[name])) options.value[name] = saved[name];
  for (const name of ['showAll', 'showMore'])
    if (typeof saved[name] === 'boolean') options.value[name] = saved[name];
  if (Number.isFinite(saved.splitterRatio))
    options.value.splitterRatio = Math.max(
      0.22,
      Math.min(0.78, saved.splitterRatio)
    );
} catch {
  /* Use native defaults when stored preferences are unavailable. */
}
const rows = ref([]),
  previews = ref([]),
  snapshots = ref([]),
  owner = ref(null),
  hasNext = ref(false);
const index = ref(0),
  selectedFile = ref(''),
  contextFile = ref(null),
  fileMenu = ref(null),
  preview = ref(null),
  form = ref(null),
  action = ref(null);
const areaSize = ref({ width: 0, height: 0 });
const panelLayout = computed(() =>
  SnapshotUI.layout(
    { ...options.value, ratio: ratio.value },
    areaSize.value.width,
    areaSize.value.height
  )
);
const panelStyle = (bounds) =>
  mobile.value
    ? undefined
    : {
        left: bounds.x + 'px',
        top: bounds.y + 'px',
        width: bounds.width + 'px',
        height: bounds.height + 'px',
        right: 'auto',
        bottom: 'auto'
      };
const area = ref(null),
  filePanel = ref(null),
  fileWidth = ref(0),
  extent = ref(0),
  moving = ref(false),
  draftRatio = ref(0.52);
const image = ref(null),
  quality = ref(''),
  outgoing = ref(''),
  incomingLayer = ref(null),
  outgoingLayer = ref(null);
let request = 0,
  observer,
  animations = [],
  transition = 0;
const showingPreview = computed(
  () =>
    options.value.contentMode !== 'files' &&
    (!mobile.value || previews.value.some((row) => row.url))
);
const showingFiles = computed(
  () =>
    (mobile.value && !showingPreview.value) ||
    options.value.contentMode !== 'preview'
);
const vertical = computed(
  () => !mobile.value && options.value.orientation === 'vertical'
);
const current = computed(() => previews.value[index.value]);
const phoneFile = computed(() =>
  rows.value.find((row) => row.token && row.token === selectedFile.value)
);
const visibleRows = computed(() =>
  rows.value.filter(
    (row) =>
      options.value.showAll ||
      (['file', 'more'].includes(row.rowType) && !row.previewType)
  )
);
const count = computed(
  () => visibleRows.value.filter((row) => row.rowType === 'file').length
);
const ratio = computed(() =>
  clamp(moving.value ? draftRatio.value : options.value.splitterRatio)
);
const imageMode = computed({
  get: () => options.value.imageMode,
  set: (value) => setOption('imageMode', value)
});
const imageIndex = computed({
  get: () => index.value,
  set: (value) => navigate(value)
});
const fileColumns = computed(() =>
  SnapshotUI.fileColumns(options.value.showMore, fileWidth.value)
);
const moreSize = computed(() => fileColumns.value.size);
const morePath = computed(() => fileColumns.value.path);
const moreRepo = computed(() => fileColumns.value.repository);
const moreBase = computed(() => fileColumns.value.base);
const canCopyImage = computed(
  () => !!navigator.clipboard?.write && !!globalThis.ClipboardItem
);

function setOption(name, value) {
  const next = { ...options.value, [name]: value };
  try {
    localStorage.setItem(
      'tactic_stream.snapshot-browser',
      JSON.stringify(next)
    );
    options.value = next;
  } catch {
    error.value = t('Browser settings could not be saved.');
  }
}
function clamp(value) {
  return SnapshotUI.clampRatio(value, extent.value, vertical.value);
}
const toolbarModel = computed(() => ({
  ...options.value,
  phone: mobile.value,
  canRefresh: !loading.value && !!props.target?.key
}));
function toolbarAction(event) {
  if (event.type === 'refresh') load();
  else if (event.type === 'image') setOption('imageMode', event.value);
}
function optionAction(command) {
  const change = SnapshotUI.optionChange(options.value, command);
  setOption(change.key, change.value);
}
function measure() {
  const box = area.value?.getBoundingClientRect();
  areaSize.value = { width: box?.width || 0, height: box?.height || 0 };
  extent.value = (vertical.value ? box?.width : box?.height) || 0;
  fileWidth.value = filePanel.value?.clientWidth || 0;
}
function drag(event) {
  if (event.button !== 0) return;
  event.preventDefault();
  event.currentTarget.setPointerCapture(event.pointerId);
  moving.value = true;
  draftRatio.value = ratio.value;
}
function resize(event) {
  if (!moving.value) return;
  const box = area.value.getBoundingClientRect();
  draftRatio.value = clamp(
    vertical.value
      ? (event.clientX - box.left) / box.width
      : (event.clientY - box.top) / box.height
  );
}
function endDrag(event) {
  if (!moving.value) return;
  if (event.type !== 'pointercancel')
    setOption('splitterRatio', clamp(draftRatio.value));
  moving.value = false;
}
function splitterKey(event) {
  const step = ['ArrowLeft', 'ArrowUp'].includes(event.key)
    ? -0.02
    : ['ArrowRight', 'ArrowDown'].includes(event.key)
      ? 0.02
      : 0;
  if (!step) return;
  event.preventDefault();
  setOption('splitterRatio', clamp(ratio.value + step));
}
function reset() {
  settle();
  request++;
  rows.value = [];
  previews.value = [];
  snapshots.value = [];
  owner.value = null;
  loading.value = false;
  loaded.value = false;
  hasNext.value = false;
  selectedFile.value = '';
  index.value = 0;
  contextFile.value = null;
  fileMenu.value?.close();
  error.value = '';
  quality.value = '';
  image.value = null;
}
async function load(append = false) {
  if (
    !props.active ||
    !props.ticket ||
    !props.target?.key ||
    props.target.project !== props.project
  )
    return;
  const id = ++request,
    key = props.target.key;
  loading.value = true;
  error.value = '';
  contextFile.value = null;
  fileMenu.value?.close();
  try {
    const value = await resultItems(
      props.ticket,
      props.project,
      key.split('?')[0],
      [key],
      {
        branch: {
          kind: 'snapshot_browser',
          process: props.target.process || ''
        },
        offset: append ? snapshots.value.length : 0,
        limit: 50
      }
    );
    if (id !== request) return;
    rows.value = append ? [...rows.value, ...value.rows] : value.rows;
    previews.value = append
      ? [...previews.value, ...value.previews]
      : value.previews;
    snapshots.value = append
      ? [...snapshots.value, ...value.snapshots]
      : value.snapshots;
    owner.value = value.owner;
    hasNext.value = value.has_next;
    loaded.value = true;
    if (!append) {
      settle();
      selectedFile.value = '';
      index.value = 0;
      quality.value = '';
      image.value = null;
    }
  } catch (reason) {
    if (id === request) {
      error.value = reason.message;
      if (reason.code === 'authentication_failed') emit('session-expired');
    }
  } finally {
    if (id === request) loading.value = false;
  }
}
async function loadMembers(row) {
  if (loading.value) return;
  const id = request;
  loading.value = true;
  error.value = '';
  try {
    const result = await resultItems(
      props.ticket,
      props.project,
      'sthpw/file',
      [row.record.__search_key__],
      {
        branch: { kind: 'snapshot_members' },
        offset: row.memberOffset,
        limit: 50
      }
    );
    if (id !== request) return;
    const position = rows.value.indexOf(row);
    if (position >= 0) rows.value.splice(position, 1, ...result.rows);
  } catch (reason) {
    if (id === request) {
      error.value = reason.message;
      if (reason.code === 'authentication_failed') emit('session-expired');
    }
  } finally {
    if (id === request) loading.value = false;
  }
}
function settle() {
  transition++;
  for (const animation of animations) animation.cancel();
  animations = [];
  outgoing.value = '';
}
async function navigate(value, animate = true) {
  const next = Math.max(0, Math.min(previews.value.length - 1, value)),
    previous = quality.value || current.value?.url;
  if (next === index.value) return;
  const direction = next >= index.value ? 1 : -1,
    id = request;
  settle();
  const generation = transition;
  index.value = next;
  quality.value = '';
  image.value = null;
  if (
    !animate ||
    !previous ||
    previous === current.value?.url ||
    !showingPreview.value
  )
    return;
  const style = getComputedStyle(document.documentElement),
    duration = parseFloat(style.getPropertyValue('--motion-extended')) || 0;
  if (!duration || document.documentElement.dataset.fadeAnimations === 'false')
    return;
  outgoing.value = previous;
  await nextTick();
  if (
    id !== request ||
    generation !== transition ||
    !incomingLayer.value ||
    !outgoingLayer.value
  )
    return;
  const distance = Math.max(36, incomingLayer.value.clientWidth * 0.18),
    slow = parseFloat(style.getPropertyValue('--motion-slow')) || duration;
  animations = [
    incomingLayer.value.animate(
      [
        { transform: `translateX(${direction * distance}px)` },
        { transform: 'translateX(0)' }
      ],
      { duration, easing: 'cubic-bezier(.19,1,.22,1)' }
    ),
    incomingLayer.value.animate([{ opacity: 0 }, { opacity: 1 }], {
      duration: slow,
      easing: 'cubic-bezier(.215,.61,.355,1)'
    }),
    outgoingLayer.value.animate(
      [
        { transform: 'translateX(0)' },
        { transform: `translateX(${-direction * distance}px)` }
      ],
      { duration, easing: 'cubic-bezier(.19,1,.22,1)' }
    ),
    outgoingLayer.value.animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: slow,
      easing: 'cubic-bezier(.215,.61,.355,1)',
      fill: 'forwards'
    })
  ];
  const batch = animations;
  try {
    await Promise.all(batch.map((animation) => animation.finished));
  } catch {
    /* A newer selection settled the previous transition. */
  }
  if (animations === batch) settle();
}
function needQuality() {
  const original = current.value?.qualityUrl,
    element = image.value;
  if (
    !element ||
    !original ||
    original === element.getAttribute('src') ||
    quality.value ||
    !element.naturalWidth
  )
    return;
  const box = element.getBoundingClientRect(),
    ratio =
      options.value.imageMode === 'fill'
        ? Math.max(
            box.width / element.naturalWidth,
            box.height / element.naturalHeight
          )
        : Math.min(
            box.width / element.naturalWidth,
            box.height / element.naturalHeight
          );
  if (ratio * devicePixelRatio > 1.2) quality.value = original;
}
async function openMenu(file, event, editing = false) {
  if (!file || !file.token || file.rowType === 'more') return;
  contextFile.value = { ...file, editing };
  await nextTick();
  fileMenu.value.openAt(event);
}
function openFile(file) {
  if (file)
    preview.value.open(file.record, {
      files: [{ ...file, filename: file.filename, type: file.fileType }],
      context: snapshots.value.find(
        (row) => row.__search_key__ === file.snapshotKey
      )?.context,
      loadFile: blob
    });
}
async function fileAction(command) {
  const file = contextFile.value,
    id = request;
  if (!file || !rows.value.some((row) => row.token === file.token)) return;
  fileMenu.value.close();
  try {
    if (command === 'open') openFile(file);
    else if (command === 'copy_path') {
      await copyText(file.fullPath);
      notify('info', 'Path copied');
    } else if (command === 'copy_web_path') {
      if (!file.href)
        throw new Error(t('No web path is configured for this file.'));
      await copyText(new URL(file.href, location.href).href);
      notify('info', 'Web link copied');
    } else if (command === 'copy_image') {
      const value = await blob(file);
      if (id === request) {
        await copyImage(value);
        notify('info', 'Image copied');
      }
    } else if (command === 'edit') form.value.open(file.record.__search_key__);
    else if (command === 'delete') action.value.open(file.record, 'delete');
  } catch (reason) {
    if (id === request) error.value = reason.message;
  }
}
function changed() {
  load();
  emit('changed');
}
function fileIcon(row) {
  return SnapshotUI.fileIcon(
    row.rowType,
    row.fileType,
    row.baseType,
    row.filename
  );
}
function size(value) {
  if (!Number.isFinite(Number(value)) || value === '') return '';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let number = Number(value),
    level = 0;
  while (number >= 1024 && level < units.length - 1) {
    number /= 1024;
    level++;
  }
  return (level ? number.toFixed(1) : number) + ' ' + units[level];
}
watch(
  () => [props.ticket, props.project, props.target],
  () => {
    reset();
    load();
  },
  { immediate: true }
);
watch(
  () => props.active,
  (value) => {
    if (value && !loaded.value) load();
  }
);
watch(
  () => [options.value.orientation, options.value.contentMode],
  () => {
    settle();
    nextTick(measure);
  }
);
watch(
  () => options.value.imageMode,
  () => nextTick(needQuality)
);
watch(
  [area, filePanel],
  (elements) => {
    observer?.disconnect();
    observer = new ResizeObserver(() => {
      measure();
      needQuality();
    });
    for (const element of elements) if (element) observer.observe(element);
  },
  { flush: 'post' }
);
onBeforeUnmount(() => {
  request++;
  settle();
  observer?.disconnect();
});
</script>

<template>
  <Teleport defer to="#dock-snapshot">
    <section
      class="snapshot-browser"
      :aria-label="t('Snapshot Browser')"
      :aria-busy="loading"
    >
      <SnapshotToolbar :model="toolbarModel" @event="toolbarAction">
        <template #options>
          <AppMenu label="Snapshot Browser options" :width="300" overlay>
            <ActionRows
              :actions="SnapshotUI.optionActions(toolbarModel)"
              @triggered="optionAction"
            />
          </AppMenu>
        </template>
      </SnapshotToolbar>
      <p v-if="error" class="error" role="alert">
        {{ t(error) }}
        <AppButton label="Retry" :disabled="loading" @click="load()" />
      </p>
      <p v-if="loading && !rows.length" role="status" class="snapshot-status">
        {{ t('Loading snapshots…') }}
      </p>
      <div
        ref="area"
        class="snapshot-area"
        :class="{
          vertical,
          combined: showingPreview && showingFiles,
          'preview-only': !showingFiles
        }"
        :style="{
          '--snapshot-ratio': ratio * 100 + '%',
          '--snapshot-gap': SnapshotUI.metrics.splitter + 'px'
        }"
      >
        <div
          v-if="showingPreview"
          class="snapshot-preview"
          :style="panelStyle(panelLayout.preview)"
          tabindex="0"
          :aria-label="t('Snapshot preview')"
          @keydown.left.prevent="navigate(index - 1)"
          @keydown.right.prevent="navigate(index + 1)"
          @wheel.prevent="navigate(index + ($event.deltaY > 0 ? 1 : -1))"
          @contextmenu.prevent="openMenu(current?.file, $event)"
          @dblclick="openFile(current?.file)"
        >
          <div
            v-if="outgoing"
            ref="outgoingLayer"
            class="snapshot-preview-layer"
            aria-hidden="true"
          >
            <ItemPreview
              class="snapshot-image"
              :source="outgoing"
              fallback-icon="movie"
              :accent="'var(--surface-high)'"
              :preview-size="58"
              :fill-mode="options.imageMode === 'fill' ? 'cover' : 'contain'"
            />
          </div>
          <div ref="incomingLayer" class="snapshot-preview-layer">
            <ItemPreview
              class="snapshot-image"
              :source="current ? quality || current.url : ''"
              fallback-icon="movie"
              :accent="'var(--surface-high)'"
              :preview-size="58"
              :fill-mode="options.imageMode === 'fill' ? 'cover' : 'contain'"
              @ready="
                image = $event;
                needQuality();
              "
            />
          </div>
          <span v-if="current" class="snapshot-counter"
            >{{ index + 1 }} / {{ previews.length }}</span
          >
          <AppButton
            v-if="current"
            class="snapshot-preview-actions"
            label="Preview actions"
            icon="more"
            icon-only
            @click.stop="openMenu(current.file, $event)"
          />
          <AppButton
            v-if="previews.length > 1"
            class="snapshot-previous"
            label="Previous preview"
            icon="chevron-left"
            icon-only
            :disabled="index === 0"
            @click.stop="navigate(index - 1)"
          />
          <AppButton
            v-if="previews.length > 1"
            class="snapshot-next"
            label="Next preview"
            icon="chevron-right"
            icon-only
            :disabled="index === previews.length - 1"
            @click.stop="navigate(index + 1)"
          />
          <MiddleElide
            v-if="current"
            class="snapshot-preview-title"
            :text="current.title"
          />
          <AppSlider
            v-if="previews.length > 1"
            v-model="imageIndex"
            class="snapshot-preview-slider"
            label="Preview number"
            :min="0"
            :max="previews.length - 1"
            :step="1"
            @dblclick.stop
            @wheel.stop
            @keydown.stop
          />
        </div>
        <div
          v-if="showingFiles"
          ref="filePanel"
          class="snapshot-files"
          :style="panelStyle(panelLayout.files)"
          :class="{
            'more-size': moreSize,
            'more-path': morePath,
            'more-repo': moreRepo,
            'more-base': moreBase
          }"
        >
          <div class="snapshot-file-head">
            <i></i
            ><strong>{{
              t(
                options.showMore
                  ? 'Files'
                  : options.showAll
                    ? 'All snapshot files'
                    : 'Published files'
              )
            }}</strong
            ><span v-if="fileWidth >= 240" class="file-count">{{
              t(count === 1 ? '{count} file' : '{count} files', { count })
            }}</span
            ><span v-if="moreSize" class="file-size">{{ t('Size') }}</span
            ><span v-if="morePath" class="file-path">{{ t('Path') }}</span
            ><span v-if="moreRepo" class="file-repo">{{ t('Repo') }}</span
            ><span v-if="moreBase" class="file-base">{{ t('Base Type') }}</span>
          </div>
          <div
            class="snapshot-file-list"
            role="listbox"
            :aria-label="t('Snapshot files')"
          >
            <component
              :is="['file', 'more'].includes(row.rowType) ? 'button' : 'div'"
              v-for="(row, position) in visibleRows"
              :key="
                row.snapshotKey +
                ':' +
                row.token +
                ':' +
                row.title +
                ':' +
                row.depth
              "
              class="snapshot-file-row"
              :class="{
                selected: row.token && selectedFile === row.token,
                header: row.rowType === 'snapshot',
                type: row.rowType === 'type',
                alternate: position % 2
              }"
              :style="{
                '--file-indent': options.showAll ? row.depth * 14 + 'px' : '0px'
              }"
              :type="row.rowType === 'file' ? 'button' : undefined"
              :role="row.rowType === 'file' ? 'option' : 'presentation'"
              :aria-selected="
                row.rowType === 'file' ? selectedFile === row.token : undefined
              "
              @click="
                row.rowType === 'more'
                  ? loadMembers(row)
                  : row.token && (selectedFile = row.token)
              "
              @dblclick="row.rowType === 'file' && row.token && openFile(row)"
              @contextmenu.prevent="openMenu(row, $event, true)"
            >
              <AppIcon
                :name="fileIcon(row)"
                :style="{
                  color:
                    row.rowType === 'file' && !row.exists
                      ? 'var(--muted)'
                      : row.rowType === 'type'
                        ? 'var(--yellow)'
                        : 'var(--primary)'
                }"
              /><MiddleElide
                :text="row.rowType === 'more' ? t(row.title) : row.title"
              />
              <span v-if="moreSize" class="file-size">{{
                row.rowType === 'file' ? size(row.size) : ''
              }}</span
              ><MiddleElide
                v-if="morePath"
                class="file-path"
                :text="row.path || ''"
              /><span v-if="moreRepo" class="file-repo">{{
                row.repository
              }}</span
              ><span v-if="moreBase" class="file-base">{{ row.baseType }}</span>
              <AppIcon
                v-if="row.rowType === 'file' && !row.exists"
                name="cloud_download"
                class="offline"
                :title="t('File Offline')"
              />
            </component>
            <p
              v-if="!loading && loaded && !visibleRows.length"
              class="snapshot-status"
            >
              {{ t('No files for this selection') }}
            </p>
            <AppButton
              v-if="hasNext"
              label="Load more snapshots"
              :disabled="loading"
              @click="load(true)"
            />
          </div>
          <footer v-if="mobile && phoneFile" class="snapshot-phone-actions">
            <MiddleElide
              :text="phoneFile.filename || phoneFile.title"
            /><AppButton
              label="Open File"
              icon="folder_open"
              icon-only
              :disabled="!phoneFile.href"
              @click="openFile(phoneFile)"
            /><AppButton
              label="Snapshot file actions"
              icon="more"
              icon-only
              @click="openMenu(phoneFile, $event, true)"
            />
          </footer>
        </div>
        <div
          v-if="showingPreview && showingFiles"
          class="snapshot-splitter resize-grip"
          :style="panelStyle(panelLayout.splitter)"
          :class="{ dragging: moving }"
          role="separator"
          tabindex="0"
          :aria-orientation="vertical ? 'vertical' : 'horizontal'"
          :aria-label="t('Resize snapshot panels')"
          :aria-valuemin="22"
          :aria-valuemax="78"
          :aria-valuenow="Math.round(ratio * 100)"
          @pointerdown="drag"
          @pointermove="resize"
          @pointerup="endDrag"
          @pointercancel="endDrag"
          @keydown="splitterKey"
        ></div>
      </div>
      <AppMenu
        ref="fileMenu"
        class="snapshot-file-menu"
        label="Snapshot file actions"
        overlay
      >
        <AppButton
          label="Open File"
          icon="folder_open"
          :disabled="!contextFile?.href"
          @click="fileAction('open')"
        />
        <AppButton
          label="Show Folder"
          icon="folder"
          disabled
          :title="t('Server folders cannot be opened by this browser.')"
        />
        <hr />
        <AppButton
          label="Copy File Path"
          icon="copy"
          @click="fileAction('copy_path')"
        /><AppButton
          label="Copy Web Link"
          icon="link"
          :disabled="!contextFile?.href"
          @click="fileAction('copy_web_path')"
        />
        <AppButton
          label="Copy To Clipboard"
          icon="copy"
          :disabled="!canCopyImage || !contextFile?.href"
          :title="
            !canCopyImage
              ? t(
                  'Copying an image requires HTTPS or localhost and clipboard permission.'
                )
              : ''
          "
          @click="fileAction('copy_image')"
        />
        <template v-if="contextFile?.editing"
          ><hr />
          <AppButton
            label="Edit Info"
            icon="edit"
            @click="fileAction('edit')" /><AppButton
            label="Delete"
            icon="delete"
            @click="fileAction('delete')"
        /></template>
      </AppMenu>
    </section>
  </Teleport>
  <FilePreview
    ref="preview"
    :ticket="ticket"
    :project="project"
    search-type="sthpw/file"
    @session-expired="emit('session-expired')"
  />
  <RecordForm
    ref="form"
    :ticket="ticket"
    :project="project"
    search-type="sthpw/file"
    @saved="changed"
  />
  <ObjectAction
    ref="action"
    :ticket="ticket"
    :project="project"
    search-type="sthpw/file"
    view="table"
    @saved="changed"
  />
</template>

<style scoped>
.snapshot-browser {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--surface-deep);
}
.snapshot-area {
  flex: 1;
  min-height: 0;
  position: relative;
  margin: 10px;
}
.snapshot-area.preview-only {
  margin: 0;
}
.snapshot-preview,
.snapshot-files {
  position: absolute;
  inset: 0;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}
.snapshot-area.combined .snapshot-preview {
  bottom: auto;
  height: calc(var(--snapshot-ratio) - var(--snapshot-gap) / 2);
}
.snapshot-area.combined .snapshot-files {
  top: calc(var(--snapshot-ratio) + var(--snapshot-gap) / 2);
}
.snapshot-area.combined.vertical .snapshot-preview {
  right: auto;
  bottom: 0;
  height: auto;
  width: calc(var(--snapshot-ratio) - var(--snapshot-gap) / 2);
}
.snapshot-area.combined.vertical .snapshot-files {
  top: 0;
  left: calc(var(--snapshot-ratio) + var(--snapshot-gap) / 2);
}
.snapshot-preview {
  border-radius: var(--item-radius);
  background: var(--surface-high);
}
.snapshot-preview-layer {
  position: absolute;
  inset: 0;
}
.snapshot-image {
  width: 100%;
  height: 100%;
  border-radius: var(--item-radius);
}
.snapshot-counter {
  position: absolute;
  right: 10px;
  top: 10px;
  height: 26px;
  line-height: 26px;
  padding: 0 8px;
  border-radius: 13px;
  background: var(--surface-high);
  font-size: var(--text-label);
}
.snapshot-preview-title {
  position: absolute;
  left: 50%;
  bottom: 7px;
  transform: translateX(-50%);
  max-width: calc(100% - 110px);
  height: 28px;
  line-height: 28px;
  padding: 0 11px;
  border-radius: 14px;
  background: var(--surface-high);
  font-size: var(--text-body);
  opacity: 0;
  transition: opacity var(--motion-fast);
}
.snapshot-preview:has(.snapshot-preview-slider) .snapshot-preview-title {
  bottom: 25px;
}
.snapshot-preview-actions {
  position: absolute;
  left: 10px;
  top: 10px;
  width: 34px;
  height: 34px;
  min-width: 34px;
  min-height: 34px;
  --icon-size: 16px;
  border: 0;
  background: var(--surface-high);
  opacity: 0;
}
.snapshot-previous,
.snapshot-next {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  min-width: 40px;
  height: 84px;
  border-radius: var(--item-radius);
  border: 0;
  background: var(--surface-high);
  opacity: 0;
  --icon-size: 18px;
}
.snapshot-previous {
  left: 10px;
}
.snapshot-next {
  right: 10px;
}
.snapshot-preview:hover .snapshot-preview-title,
.snapshot-preview:hover .snapshot-preview-actions,
.snapshot-preview:hover .snapshot-previous,
.snapshot-preview:hover .snapshot-next,
.snapshot-preview:focus-within .icon-button {
  opacity: 0.92;
}
.snapshot-preview-slider {
  position: absolute;
  width: calc(100% - 24px);
  left: 12px;
  right: 12px;
  bottom: 3px;
  height: 18px;
}
.snapshot-files {
  display: flex;
  flex-direction: column;
  border-radius: 12px;
  background: var(--surface);
  border: 1px solid var(--outline);
}
.snapshot-file-head {
  height: 35px;
  flex: none;
  margin: 0 9px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: var(--text-label);
}
.snapshot-file-head i {
  width: 4px;
  height: 18px;
  flex: none;
  border-radius: 2px;
  background: var(--primary);
}
.snapshot-file-head strong {
  flex: 1;
  min-width: 40px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-body);
  font-weight: 600;
}
.snapshot-file-head .file-count {
  flex: none;
}
.snapshot-file-list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}
.snapshot-file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  text-align: left;
  width: calc(100% - 4px);
  min-height: 0;
  height: 30px;
  margin: 0 2px;
  padding: 0 8px 0 calc(8px + var(--file-indent));
  border: 0;
  border-radius: 8px;
  font-weight: 400;
  background: transparent;
  font-size: var(--text-body);
  color: var(--on-surface);
  cursor: default;
}
.snapshot-file-row.header {
  height: 32px;
  background: var(--surface-high);
  font-weight: 600;
}
.snapshot-file-row.type {
  font-weight: 600;
}
.snapshot-file-row.alternate {
  background: var(--row);
}
.snapshot-file-row > .app-icon {
  flex: none;
  --icon-size: 15px;
}
.snapshot-file-row > .middle-elide {
  min-width: 40px;
  flex: 1;
}
.snapshot-file-row.selected {
  background: var(--selected);
}
.snapshot-file-row:not(.header):not(.type):hover {
  background: var(--hover);
}
.file-size,
.file-path,
.file-repo,
.file-base {
  flex: none !important;
  color: var(--muted);
  font-size: var(--text-label);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.file-size {
  width: 54px;
  text-align: right;
}
.file-path {
  width: 170px;
}
.file-repo {
  width: 64px;
}
.file-base {
  width: 70px;
}
.snapshot-file-row .offline {
  color: var(--error);
  --icon-size: 14px;
}
.snapshot-splitter {
  position: absolute;
  left: 0;
  top: calc(var(--snapshot-ratio) - var(--snapshot-gap) / 2);
  width: 100%;
  height: var(--snapshot-gap);
  cursor: ns-resize;
  touch-action: none;
}
.vertical .snapshot-splitter {
  top: 0;
  left: calc(var(--snapshot-ratio) - var(--snapshot-gap) / 2);
  width: var(--snapshot-gap);
  height: 100%;
  cursor: ew-resize;
}
.snapshot-file-menu {
  position: absolute;
  width: 0;
  height: 0;
  overflow: visible;
}
.snapshot-file-menu :deep(summary) {
  display: none;
}
.snapshot-status {
  color: var(--muted);
  font-size: var(--text-label);
  padding: 8px 10px;
  margin: 0;
}
.snapshot-browser > .error {
  flex: none;
  margin: 8px;
}
@media (max-width: 700px) {
  .snapshot-area {
    display: flex;
    flex-direction: column;
    margin: 0;
  }
  .snapshot-area .snapshot-preview,
  .snapshot-area.combined .snapshot-preview,
  .snapshot-area.vertical .snapshot-preview {
    position: relative;
    inset: auto;
    width: 100%;
    height: auto;
    flex: 0 1 36%;
    min-height: 110px;
    border: 0;
    border-radius: 0;
  }
  .snapshot-area .snapshot-files,
  .snapshot-area.combined .snapshot-files,
  .snapshot-area.vertical .snapshot-files {
    position: relative;
    inset: auto;
    width: 100%;
    height: auto;
    flex: 1;
    min-height: 0;
    border: 0;
    border-radius: 0;
  }
  .snapshot-splitter {
    display: none;
  }
  .snapshot-preview-actions,
  .snapshot-previous,
  .snapshot-next {
    opacity: 0.92;
  }
  .snapshot-phone-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px 6px;
    border-top: 1px solid var(--outline-variant);
  }
  .snapshot-phone-actions > .middle-elide {
    flex: 1;
    min-width: 0;
  }
  .snapshot-phone-actions > .icon-button {
    width: 28px;
    height: 28px;
    min-height: 0;
  }
}
</style>
