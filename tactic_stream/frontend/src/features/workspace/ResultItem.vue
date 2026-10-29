<script setup>
import { computed, inject, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { t } from '../../i18n.js';
import ResultBody from './ResultBody.vue';
import FrameView from '../../frame/FrameView.vue';
import { appearance, readableText, frameColors } from '../../appearance.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { fontFamily } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import StatusChip from '../../controls/display/StatusChip.vue';
import InfoValueStrip from '../../controls/layout/InfoValueStrip.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import * as Card from '../../../../src/tactic_stream/shared_ui/features/search/card.ui.mjs';
import AppButton from '../../controls/AppButton.vue';
import DisclosureButton from '../../controls/actions/DisclosureButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import AppMenu from '../../controls/AppMenu.vue';
import AppMenuItem from '../../controls/AppMenuItem.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import { mobile } from '../../mobile.js';
import { prettySize } from '../checkin/files.js';
import { timestampLabel, timestampFullLabel } from '../activity/activity.js';
import MiddleElide from '../../controls/MiddleElide.vue';
import BranchFilter from './BranchFilter.vue';

const props = defineProps({
  node: Object,
  compact: Boolean,
  card: Boolean,
  tree: Boolean,
  selected: Boolean,
  checked: Boolean,
  selectable: Boolean,
  back: Boolean,
  navigable: { type: Boolean, default: true }
});
const openObjectTab = inject('openObjectTab', null);
defineEmits([
  'back',
  'opencard',
  'upload',
  'expand',
  'activate',
  'doubleclick',
  'newtab',
  'quickaction',
  'relations',
  'inspect',
  'operate',
  'select',
  'preview',
  'notes',
  'tasks',
  'create',
  'completion',
  'link',
  'filter'
]);
const record = computed(() => props.node.record || {});
const previewSource = computed(() => {
  const preview = props.node.preview;
  return mobile.value && props.node.kind === 'object'
    ? preview?.files?.find((file) => file.type === 'web' && file.href)?.href ||
        preview?.image
    : preview?.image;
});
const tileShadeStyle = computed(() => ({
  background: `linear-gradient(to bottom, ${Card.tileShade
    .map(
      (stop) =>
        `color-mix(in srgb, var(${props.selected ? '--content-selection' : '--surface-high'}) ${stop.opacity * 100}%, transparent) ${stop.position * 100}%`
    )
    .join(', ')})`
}));
const title = computed(() =>
  props.node.kind === 'snapshot' && props.node.snapshot_display
    ? props.node.snapshot_display.multiple
      ? t('Multiple files | {count}', {
          count: props.node.snapshot_display.multiple
        })
      : props.node.snapshot_display.title
    : props.node.title ||
      record.value.name ||
      record.value.title ||
      record.value.code ||
      String(record.value.id || '')
);
// Handler global_functions.gen_acronym: capital letters, then the first letters
// as fallback. Numbers are not words ("Episode 01 — Arrival" becomes EA).
const initials = computed(() => {
  const text = title.value[0]?.toUpperCase() + title.value.slice(1);
  let acronym = [...text]
    .filter((char) => /[\p{Lu}]/u.test(char))
    .slice(0, 2)
    .join('');
  if (acronym.length < 2) acronym += text.slice(1, 2);
  return acronym.toUpperCase() || '?';
});
const branch = computed(() => props.node.kind === 'branch');
const relation = computed(() => props.node.branch?.kind === 'relation');
const process = computed(() => props.node.branch?.kind === 'process');
const filterable = computed(
  () =>
    !props.card &&
    !mobile.value &&
    props.node.expanded &&
    props.node.loaded &&
    (relation.value || process.value)
);
const accent = computed(
  () => props.node.accent || record.value.color || 'var(--content-accent)'
);
const subtitle = computed(
  () =>
    props.node.subtitle ||
    record.value.description ||
    (props.node.kind === 'snapshot' ? t('No description') : '')
);
const host = ref(null),
  hostWidth = ref(0);
const cardModel = computed(() => ({
  kind:
    props.node.kind === 'branch'
      ? props.node.branch?.kind === 'relation'
        ? 'relation'
        : 'process'
      : props.node.kind,
  compact: props.compact,
  depth: props.node.depth || 0,
  hasChildren: props.node.hasChildren,
  subtitle: subtitle.value,
  selected: props.selected,
  mobile: mobile.value,
  tile: props.card,
  hasMetadata:
    !!props.node.progress_items?.length || !!props.node.info_items?.length,
  technical:
    props.node.kind === 'snapshot'
      ? [
          props.node.snapshot_display?.version,
          record.value.context,
          props.node.snapshot_display?.repository
        ]
          .filter(Boolean)
          .join(' · ')
      : process.value
        ? [props.node.branch.process || title.value, record.value.status]
            .filter(Boolean)
            .join(' · ')
        : [record.value.status, props.node.snapshot_display?.author]
            .filter(Boolean)
            .join(' · ')
}));
const typeTitle = computed(() =>
  props.node.kind === 'object'
    ? (
        props.node.searchType ||
        record.value.__search_key__?.split('?')[0] ||
        ''
      )
        .split('/')
        .at(-1)
        ?.replaceAll('_', ' ')
        .replace(/^./, (value) => value.toUpperCase()) || 'SObject'
    : relation.value
      ? title.value
      : process.value
        ? 'PROCESS'
        : props.node.kind === 'snapshot'
          ? 'SNAPSHOT'
          : 'FILE'
);
const typeIcon = computed(() =>
  props.node.kind === 'object'
    ? 'sobject'
    : process.value
      ? 'cogs'
      : relation.value
        ? 'project-diagram'
        : props.node.kind === 'snapshot'
          ? 'camera'
          : 'file'
);
const headerScene = computed(() =>
  Card.tileHeader(
    {
      ...cardModel.value,
      typeTitle: typeTitle.value,
      typeIcon: typeIcon.value,
      typeColor: props.node.kind === 'snapshot' ? 'cyan' : accent.value,
      foreground: readableText(
        props.node.kind === 'snapshot'
          ? frameColors.value.cyan
          : /^#[a-f0-9]{6}$/i.test(accent.value)
            ? [1, 3, 5].map((offset) =>
                parseInt(accent.value.slice(offset, offset + 2), 16)
              )
            : frameColors.value.contentAccent
      ),
      typeWidth: qtLabelTextWidth(
        typeTitle.value,
        '700 11px "' + fontFamily + '"'
      )
    },
    hostWidth.value - 16,
    appearance.language
  )
);
const branchScene = computed(() =>
  Card.branchPreview(
    {
      kind: cardModel.value.kind,
      typeColor: accent.value,
      count: props.node.branch?.count || 0
    },
    Math.max(0, hostWidth.value - 16),
    geometry.value.header?.height || 0,
    appearance.language
  )
);
const previewOverlay = computed(() =>
  Card.previewOverlay(
    {
      latest:
        props.node.kind === 'snapshot' && !!props.node.snapshot_display?.latest,
      textWidth: qtLabelTextWidth(t('LATEST'), '700 11px "' + fontFamily + '"'),
      foreground: readableText(frameColors.value.action)
    },
    geometry.value.preview.width,
    appearance.language
  )
);
const geometry = computed(() => Card.layout(cardModel.value, hostWidth.value));
const bounds = (part) => ({
  position: 'absolute',
  left: part.x + 'px',
  top: part.y + 'px',
  width: part.width + 'px',
  height: part.height + 'px'
});
let sizeObserver;
onMounted(() => {
  hostWidth.value = host.value.clientWidth;
  sizeObserver = observeFrameSizes((entries) => {
    hostWidth.value = entries.at(-1).contentRect.width;
  });
  sizeObserver.observe(host.value);
});
onBeforeUnmount(() => sizeObserver?.disconnect());
const controlHover = ref(false),
  titleActionsFit = ref(true);
let hoverTimer;
function holdControls() {
  clearTimeout(hoverTimer);
  controlHover.value = true;
}
function releaseControls() {
  clearTimeout(hoverTimer);
  hoverTimer = setTimeout(() => {
    if (!props.node.menuVisible) controlHover.value = false;
  }, 500);
}
function fitTitleActions(event) {
  if (mobile.value || !props.tree || props.node.kind !== 'object') return;
  const line = event.currentTarget,
    count = line.querySelectorAll('.result-title-actions button').length;
  titleActionsFit.value =
    line.querySelector('strong').scrollWidth +
      8 +
      count * 28 +
      Math.max(0, count - 1) * 5 <=
    line.parentElement.clientWidth;
}
watch(
  () => props.node.menuVisible,
  (visible) => {
    if (!visible) releaseControls();
  }
);
onBeforeUnmount(() => clearTimeout(hoverTimer));
</script>

<template>
  <article
    ref="host"
    class="result-item result-frame-card"
    :class="{
      'result-item-compact': compact,
      'result-item-card': card,
      'result-item-branch': branch,
      'result-mobile-header': back,
      'result-item-object': node.kind === 'object',
      'result-item-relation': relation,
      'result-item-process': process,
      'result-item-snapshot': node.kind === 'snapshot',
      'result-item-tree': tree,
      'menu-open': node.menuVisible,
      'control-hover': controlHover,
      selected
    }"
    :style="{
      '--result-depth': node.depth || 0,
      '--result-accent': accent,
      height: geometry.height + 'px',
      minHeight: geometry.height + 'px',
      padding: 0
    }"
    :data-result-key="record.__search_key__"
    :data-node-id="node.id"
    :aria-label="title"
    tabindex="0"
    @click="$emit('activate', node, $event)"
    @keydown.enter.self.prevent="
      $emit(card ? 'opencard' : 'activate', node, $event)
    "
    @keydown.space.self.prevent="
      $emit(card ? 'opencard' : 'activate', node, $event)
    "
    @dblclick="
      (event) => {
        if (!event.target.closest('button,a,summary'))
          $emit('doubleclick', node, event);
      }
    "
    @auxclick.middle.prevent="
      (event) => {
        if (!event.target.closest('button,a,summary')) {
          $emit('activate', node, event);
          $emit('newtab', node);
        }
      }
    "
    @keydown.right.self.prevent.stop="
      mobile
        ? navigable && $emit('activate', node, $event)
        : $emit('expand', node, true, $event)
    "
    @keydown.left.self.prevent.stop="
      !mobile && $emit('expand', node, false, $event)
    "
    @contextmenu.prevent.stop="
      (event) => {
        if (!mobile && !selected) $emit('activate', node, event);
        $emit('operate', node, event);
      }
    "
  >
    <span class="result-surface" aria-hidden="true"></span>
    <span
      v-for="depth in node.depth || 0"
      :key="depth"
      class="result-guide"
      :class="{ 'result-guide-elbow': depth === node.depth }"
      :style="{ left: 11 + (depth - 1) * 24 + 'px' }"
      aria-hidden="true"
    ></span>
    <AppIcon
      v-if="mobile && navigable"
      class="result-mobile-next"
      name="MDI_CHEVRON_RIGHT"
    />
    <AppButton
      v-if="mobile && back"
      class="result-mobile-back"
      label="Back"
      icon="MDI_ARROW_LEFT"
      icon-only
      @click.stop="$emit('back')"
    />
    <DisclosureButton
      v-else-if="!mobile && !card && node.hasChildren"
      class="result-expand"
      :style="bounds(geometry.disclosure)"
      :identity="node.id"
      :has-children="node.hasChildren"
      :expanded="!!node.expanded"
      :loading="!!node.busy"
      :icon-size="
        node.kind === 'object' ? (compact ? 14 : 18) : branch ? 13 : 15
      "
      :indicator-size="node.kind === 'object' ? (compact ? 20 : 24) : 18"
      @click.stop="$emit('expand', node, undefined, $event)"
    />
    <span
      v-else-if="!mobile && !card"
      class="result-expand-spacer"
      :style="bounds(geometry.disclosure)"
    ></span>
    <component
      :is="tree || mobile || card ? 'span' : 'button'"
      v-if="node.kind !== 'branch'"
      class="result-preview"
      :style="bounds(geometry.preview)"
      :aria-label="tree || mobile ? undefined : t('File preview')"
      @click="
        (event) => {
          if (!tree && !mobile && !card) {
            event.stopPropagation();
            $emit('preview', node);
          }
        }
      "
    >
      <ItemPreview
        :source="previewSource"
        :fallback-text="
          card && node.kind === 'snapshot'
            ? title.match(/\.([^.\\/\s]+)$/)?.[1]?.toUpperCase() || 'FILE'
            : node.kind === 'object' && !card
              ? initials
              : ''
        "
        :fallback-icon="
          node.snapshot_display?.multiple
            ? 'folder'
            : node.snapshot_display && !node.snapshot_display.exists
              ? 'FAS_EXCLAMATION_CIRCLE'
              : card
                ? typeIcon
                : 'file'
        "
        :round="node.kind === 'object' && !card"
        :selected="selected"
        :accent="accent"
        :preview-size="geometry.preview.width"
        :style="{
          width: geometry.preview.width + 'px',
          height: geometry.preview.height + 'px',
          flexBasis: geometry.preview.width + 'px'
        }"
      />
    </component>
    <FrameView
      v-if="card && node.kind === 'snapshot'"
      :scene="previewOverlay"
      :style="bounds(geometry.preview)"
      :interactive="false"
    />
    <span
      v-if="node.kind === 'branch' && !card"
      class="result-branch-icon"
      v-show="!filterable"
      :style="bounds(geometry.preview)"
      ><AppIcon
        :name="
          process
            ? node.branch.process_type === 'hierarchy'
              ? 'FAS_CODE_BRANCH'
              : 'FAS_CIRCLE'
            : 'stream'
        "
    /></span>
    <FrameView
      v-if="card && branch"
      :scene="branchScene"
      :style="bounds(geometry.header)"
      :interactive="false"
    />
    <span
      v-if="card && node.kind === 'object'"
      class="result-tile-shade"
      :style="tileShadeStyle"
      aria-hidden="true"
    ></span>
    <FrameView
      v-if="card"
      :scene="headerScene"
      class="result-tile-header"
      :style="bounds(geometry.header)"
      @click.stop
      @event="
        (action) => {
          if (action.type === 'open') $emit('opencard', node, $event);
        }
      "
    />
    <BranchFilter
      v-if="filterable"
      :style="bounds(geometry.preview)"
      :text="node.filterText || ''"
      :count="node.children.length"
      :more="node.hasNext"
      :busy="node.busy"
      @filter="(value) => $emit('filter', node, value)"
    />
    <div class="result-item-copy" :style="bounds(geometry.content)">
      <ResultBody
        :model="cardModel"
        :width="geometry.content.width"
        :height="geometry.content.height"
      >
        <template #title>
          <div
            class="result-title-line"
            @pointerenter="fitTitleActions"
            @focusin="fitTitleActions"
          >
            <AppIcon
              v-if="node.kind === 'file'"
              :name="
                node.snapshot_display?.exists === false
                  ? 'priority_high'
                  : 'description'
              "
            />
            <component :is="back ? 'h2' : 'strong'"
              ><MiddleElide
                v-if="tree && !mobile && node.kind === 'snapshot'"
                :text="title"
              /><template v-else>{{
                node.branch?.kind === 'versions' ? t(title) : title
              }}</template></component
            >
            <span
              v-if="tree && !branch"
              class="result-title-actions"
              :class="{ 'actions-fit': titleActionsFit }"
              @click.stop
            >
              <AppButton
                v-if="node.kind === 'object' || node.kind === 'snapshot'"
                label="Save snapshot"
                icon="save"
                icon-only
                @click="$emit('quickaction', node, 'save')"
              />
              <AppButton
                v-if="node.kind === 'snapshot' || node.has_snapshot"
                label="Open snapshot"
                icon="folder-open"
                icon-only
                @click="$emit('quickaction', node, 'open')"
              />
            </span>
            <span
              v-if="
                tree &&
                node.kind === 'snapshot' &&
                title &&
                !node.snapshot_display?.exists
              "
              class="result-file-offline"
              >({{ t('File Offline') }})</span
            >
          </div>
        </template>
        <template #metadata>
          <div v-if="node.kind === 'object'" class="result-metadata">
            <StatusChip
              v-for="item in compact
                ? node.progress_items?.slice(0, 1)
                : node.progress_items"
              :key="item.name"
              class="result-completion"
              icon="donut-small"
              :accent="item.accent || accent"
              :dense="compact"
              interactive
              :maximum-width="geometry.content.width"
              :text="
                item.name +
                ': ' +
                (item.label || item.approved + ' / ' + item.total)
              "
              :title="t('Open tracked objects')"
              @click.stop="$emit('completion', node, item)"
            />
            <span
              v-if="node.progress_items?.length && node.info_items?.length"
              class="muted"
              >|</span
            >
            <InfoValueStrip
              :items="node.info_items || []"
              :selected="selected"
              separator="|"
              @click.stop
            />
          </div>
        </template>
        <template #technical>
          <span v-if="node.kind === 'file'" class="muted">{{
            [record.relative_dir, record.file_name].filter(Boolean).join('/') ||
            node.subtitle
          }}</span>
          <template v-else-if="tree && !mobile && node.kind === 'snapshot'">
            <div class="result-snapshot-technical">
              <span class="result-snapshot-version">{{
                node.snapshot_display?.version
              }}</span
              ><span v-if="node.snapshot_display?.revision">{{
                node.snapshot_display.revision
              }}</span
              ><span
                v-if="record.repo"
                :style="{ color: node.snapshot_display?.repositoryColor }"
                >{{ node.snapshot_display?.repository || record.repo }}</span
              ><small
                v-if="node.snapshot_display?.latest"
                class="result-snapshot-latest"
                >{{ t('Latest') }}</small
              >
              <time
                class="result-snapshot-date"
                :datetime="record.timestamp"
                :title="timestampFullLabel(record.timestamp)"
                ><span>{{ timestampLabel(record.timestamp) }}</span
                ><span>{{ timestampFullLabel(record.timestamp) }}</span></time
              >
            </div>
          </template>
          <template v-else>
            <small v-if="node.kind === 'snapshot'" class="muted"
              >{{ record.context }} ·
              <template v-if="record.version < 0">{{
                t('Versionless')
              }}</template
              ><template v-else
                >{{ t('Version') }} {{ record.version }}</template
              ></small
            >
            <small
              v-else-if="mobile && branch"
              class="result-branch-summary muted"
              >{{ t(relation ? 'Objects' : 'Versions') }}:
              {{ node.branch.count ?? node.children?.length ?? 0
              }}<template v-if="node.hasNext">+</template
              ><template
                v-if="process && !node.branch.count && node.hasChildren"
              >
                · {{ t('Versionless') }}</template
              ></small
            >
          </template>
        </template>
        <template #description>
          <div class="result-snapshot-description">
            <em v-if="node.snapshot_display?.author"
              >{{ node.snapshot_display.author }}{{ subtitle ? ':' : '' }}</em
            ><span>{{ subtitle }}</span
            ><small
              ><template
                v-for="(chip, index) in node.snapshot_display?.infoChips"
                :key="chip.label"
                ><template v-if="index"> | </template
                ><span :title="chip.label + ': ' + chip.value">{{
                  chip.value
                }}</span></template
              ></small
            >
          </div>
        </template>
      </ResultBody>
    </div>
    <AppButton
      v-if="card && relation && node.hasChildren"
      class="result-tile-enter"
      icon="chevron_right"
      label="Open"
      @click.stop="$emit('opencard', node, $event)"
    />
    <div
      class="result-item-actions"
      :style="card ? { position: 'absolute', inset: 0 } : undefined"
      @click.stop
      @pointerenter="holdControls"
      @pointerleave="releaseControls"
    >
      <div
        v-if="
          mobile &&
          (node.kind === 'object' ||
            process ||
            (back && node.kind === 'snapshot'))
        "
        class="result-mobile-actions"
      >
        <template v-if="node.kind === 'object' || process">
          <AppButton
            label="Tasks"
            icon="FAR_CALENDAR_CHECK"
            icon-only
            :badge-count="node.task_count || 0"
            @click="$emit('tasks', node, $event)"
          />
          <AppButton
            label="Notes"
            icon="FAS_COMMENT_ALT"
            icon-only
            :badge-count="node.note_count || 0"
            @click="$emit('notes', node, $event)"
          />
        </template>
        <AppButton
          label="Add files"
          icon="upload"
          icon-only
          @click="$emit('upload', node)"
        />
      </div>
      <span
        v-if="
          tree &&
          node.kind === 'snapshot' &&
          node.snapshot_display?.size != null
        "
        class="result-snapshot-size"
        >{{ prettySize(node.snapshot_display.size) }}</span
      >
      <AppMenu v-if="mobile" label="Item actions" overlay>
        <AppCheckbox
          v-if="selectable"
          label="Select record"
          :model-value="checked"
          @update:model-value="$emit('select', node, $event)"
        />
        <AppMenuItem
          v-if="!branch"
          label="Object details"
          icon="MDI_INFORMATION_OUTLINE"
          @click="$emit('inspect', node)"
        />
        <AppMenuItem
          v-if="!branch"
          label="File preview"
          icon="image"
          @click="$emit('preview', node)"
        />
        <template v-if="node.kind === 'object' || process">
          <AppMenuItem
            label="Tasks"
            icon="FAR_CALENDAR_CHECK"
            @click="$emit('tasks', node, $event)"
          />
          <AppMenuItem
            label="Notes"
            icon="FAS_COMMENT_ALT"
            @click="$emit('notes', node, $event)"
          />
        </template>
        <template v-if="relation">
          <AppMenuItem
            v-if="node.branch.relationship === 'instance'"
            label="Link existing objects"
            icon="link"
            @click="$emit('link', node)"
          />
          <AppMenuItem
            label="Create related object"
            icon="add"
            @click="$emit('create', node)"
          />
        </template>
        <AppMenuItem
          v-for="article in node.knowledge || []"
          :key="article.identity"
          :label="article.title"
          :translate="false"
          icon="book-open"
          @click="openObjectTab?.(article.searchKey)"
        />
        <AppMenuItem
          label="Object actions"
          icon="more"
          @click="$emit('operate', node, $event)"
        />
      </AppMenu>
      <template v-else>
        <div v-if="tree && node.kind === 'object'" class="result-hover-actions">
          <AppButton
            label="Related and child objects"
            icon="FAS_SITEMAP"
            icon-only
            @click="$emit('relations', node, $event)"
          />
        </div>
        <div v-else-if="!tree" class="result-hover-actions">
          <AppButton
            v-if="!branch"
            class="result-details"
            label="Object details"
            icon="MDI_INFORMATION_OUTLINE"
            icon-only
            @click="$emit('inspect', node)"
          />
          <AppButton
            label="Object actions"
            icon="more"
            icon-only
            @click="$emit('operate', node, $event)"
          />
        </div>
        <template v-if="relation"
          ><AppButton
            v-if="node.branch.relationship === 'instance'"
            label="Link existing objects"
            icon="link"
            icon-only
            @click="$emit('link', node)"
          />
          <AppButton
            label="Create related object"
            icon="add"
            icon-only
            @click="$emit('create', node)"
          />
          <small
            v-if="node.branch.count > 0"
            class="result-relation-count muted"
            >| &nbsp;{{ node.branch.count }}</small
          ></template
        >
        <AppButton
          v-if="node.knowledge?.length === 1"
          icon-only
          icon="book-open"
          label="Knowledge Base"
          @click="openObjectTab?.(node.knowledge[0].searchKey)"
        />
        <AppMenu
          v-else-if="node.knowledge?.length > 1"
          icon="book-open"
          label="Knowledge Base"
          overlay
          ><AppMenuItem
            v-for="article in node.knowledge"
            :key="article.identity"
            :label="article.title"
            icon="file"
            @click="openObjectTab?.(article.searchKey)"
        /></AppMenu>
        <div
          v-if="node.kind === 'object' || process"
          class="result-communication"
          :style="card ? bounds(geometry.counts) : undefined"
          :class="{
            'result-communication-empty':
              process && !node.task_count && !node.note_count
          }"
        >
          <AppButton
            class="result-task-button"
            label="Tasks"
            icon="FAR_CALENDAR_CHECK"
            icon-only
            :badge-count="node.task_count || 0"
            @click="$emit('tasks', node, $event)"
          />
          <AppButton
            class="result-note-button"
            label="Notes"
            icon="FAS_COMMENT_ALT"
            icon-only
            :badge-count="node.note_count || 0"
            @click="$emit('notes', node, $event)"
          />
        </div>
      </template>
    </div>
  </article>
</template>

<style>
.result-item-card.result-frame-card {
  display: block;
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface-high);
}
.result-item-card.result-frame-card .result-surface {
  display: none;
}
.result-item-card .result-preview {
  z-index: 0;
}
.result-item-card.result-item-object .result-preview .image-picker-preview {
  border-radius: 12px;
}
.result-tile-shade {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.result-item-card .result-tile-header,
.result-item-card .result-item-copy {
  z-index: 3;
}
.result-item-card .result-title-line strong {
  font-size: 14px;
  font-weight: 700;
}
.result-item-card .result-hover-actions {
  position: absolute;
  right: 8px;
  top: 8px;
}
.result-item-card .result-item-actions {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.result-item-card .result-item-actions button {
  pointer-events: auto;
}
.result-item-card .result-communication {
  position: absolute;
  right: 8px;
  bottom: 7px;
  opacity: 0;
  gap: 3px;
}
.result-item-card:hover .result-communication,
.result-item-card:focus-within .result-communication,
.result-item-card .result-communication:has(.app-button-badge) {
  opacity: 1;
}
.result-item-card .result-communication .icon-button {
  width: 30px;
  height: 30px;
  min-width: 30px;
  min-height: 26px;
}
.result-item-card .result-tile-enter {
  position: absolute;
  left: 8px;
  bottom: 8px;
  width: calc(100% - 16px);
  height: 28px;
  min-height: 28px;
  z-index: 4;
}
.result-item-card .result-metadata {
  flex-wrap: wrap;
  gap: 4px;
  overflow: hidden;
}
.result-item-card .result-metadata > .info-value-strip {
  width: 100%;
}
.result-item-card .result-branch-icon {
  top: 28px;
  left: calc(50% - 24px);
  width: 48px;
  height: 48px;
}
.result-item-card .result-branch-icon .app-icon {
  font-size: 34px;
  width: 34px;
  height: 34px;
}
</style>
