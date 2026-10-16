<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { t } from '../../i18n.js';
import { appearance } from '../../appearance.js';
import AppButton from '../../controls/AppButton.vue';
import AppCheckbox from '../../controls/AppCheckbox.vue';
import FrameView from '../../frame/FrameView.vue';
import ProjectCard from './ProjectCard.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import {
  popup as popupBounds,
  header,
  category,
  categoryHeader,
  dimensions,
  keyTarget
} from '../../../../src/tactic_stream/shared_ui/shell/projects.ui.mjs';
const props = defineProps({
  projects: { type: Array, default: () => [] },
  selected: String,
  inline: Boolean
});
const emit = defineEmits(['selected']);
const popup = ref(null),
  viewportWidth = ref(innerWidth),
  viewportHeight = ref(innerHeight),
  inlineWidth = ref(760);
const showRetired = ref(false),
  showTemplates = ref(false),
  showBuiltins = ref(false);
const retired = (item) =>
  String(item.s_status || '').toLowerCase() === 'retired';
const template = (item) =>
  item.is_template === true ||
  item.is_template === 1 ||
  ['true', 't', '1'].includes(String(item.is_template).toLowerCase());
const filters = computed(() => [
  {
    key: 'retired',
    label: 'Retired',
    value: showRetired,
    count: props.projects.filter(retired).length
  },
  {
    key: 'templates',
    label: 'Templates',
    value: showTemplates,
    count: props.projects.filter(template).length
  },
  {
    key: 'builtins',
    label: 'Built-in',
    value: showBuiltins,
    count: props.projects.filter((item) => item.__builtin__).length
  }
]);
function setFilter(key, value) {
  ({ retired: showRetired, templates: showTemplates, builtins: showBuiltins })[
    key
  ].value = value;
}
const visibleProjects = computed(() =>
  props.projects.filter((item) =>
    item.__builtin__
      ? showBuiltins.value
      : template(item)
        ? showTemplates.value
        : showRetired.value || !retired(item)
  )
);
const phone = computed(() => viewportWidth.value < 620);
const size = computed(() =>
  props.inline
    ? { width: inlineWidth.value, height: 600 }
    : popupBounds(viewportWidth.value, viewportHeight.value, phone.value)
);
const heading = computed(() =>
  header(
    size.value.width,
    visibleProjects.value.length,
    props.projects.length,
    t,
    props.inline,
    phone.value
  )
);
const chrome = computed(() => ({
  ...heading.value,
  nodes: heading.value.nodes.filter((node) => node.kind !== 'View')
}));
const categoryWidth = computed(() => Math.max(0, size.value.width - 36));
const groups = computed(() => {
  const result = new Map();
  for (const item of visibleProjects.value) {
    const title = item.category || '';
    if (!result.has(title)) result.set(title, []);
    result.get(title).push({
      ...item,
      initials: (item.title || item.code)
        .replaceAll('_', ' ')
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0])
        .join('')
        .toUpperCase(),
      projectType: item.type || '',
      isBuiltin: !!item.__builtin__,
      isTemplate: template(item),
      isRetired: retired(item)
    });
  }
  return [...result].map(([title, projects]) => ({
    title,
    projects,
    layout: category(categoryWidth.value, projects.length, phone.value)
  }));
});
function close() {
  if (!props.inline) popup.value.hidePopover();
}
function choose(code) {
  emit('selected', code);
  close();
}
function move(event) {
  const current = event.target.closest('[data-project]')?.dataset.project;
  if (!current) return;
  const codes = groups.value.flatMap((group) =>
    group.projects.map((item) => item.code)
  );
  const target = keyTarget(
    codes,
    current,
    event.key,
    category(categoryWidth.value, 1, phone.value).columns
  );
  if (!target) return;
  event.preventDefault();
  [...popup.value.querySelectorAll('[data-project]')]
    .find((node) => node.dataset.project === target)
    ?.querySelector('button')
    ?.focus();
}
function resized() {
  viewportWidth.value = innerWidth;
  viewportHeight.value = innerHeight;
}
let observer;
onMounted(() => {
  window.addEventListener('resize', resized);
  if (props.inline) {
    observer = observeFrameSizes(
      (entries) => (inlineWidth.value = entries.at(-1).contentRect.width)
    );
    observer.observe(popup.value);
  }
});
onBeforeUnmount(() => {
  window.removeEventListener('resize', resized);
  observer?.disconnect();
});
</script>
<template>
  <div
    ref="popup"
    :id="inline ? undefined : 'project-chooser'"
    class="project-chooser frame-project-chooser"
    :class="{ 'project-catalog-inline': inline }"
    :popover="inline ? undefined : 'auto'"
    :role="inline ? 'region' : 'dialog'"
    :aria-label="t('Projects')"
    :style="{
      '--project-popup-width': size.width + 'px',
      '--project-popup-height': size.height + 'px',
      '--project-header-height': heading.height + 'px',
      '--project-filter-padding': dimensions.filterPadding + 'px'
    }"
    @keydown.esc.stop
    @keydown="move"
  >
    <div class="project-header" :style="{ height: heading.height + 'px' }">
      <FrameView :scene="chrome" :interactive="false" />
      <AppButton
        v-if="!inline"
        class="project-close"
        icon-only
        label="Close"
        icon="close"
        @click="close"
      />
      <div class="project-filters">
        <AppCheckbox
          v-for="filter in filters"
          :key="filter.key"
          compact
          :model-value="filter.value.value"
          :label="filter.label"
          @update:model-value="setFilter(filter.key, $event)"
          ><span>{{ t(filter.label) }} · {{ filter.count }}</span></AppCheckbox
        >
      </div>
    </div>
    <div
      class="project-categories"
      tabindex="0"
      :aria-label="t('Available projects')"
    >
      <section
        v-for="group in groups"
        :key="group.title"
        :style="{
          height: group.layout.height + 'px',
          width: categoryWidth + 'px'
        }"
      >
        <FrameView
          class="project-category-heading"
          :scene="
            categoryHeader(categoryWidth, group.title, group.projects.length, t)
          "
          :interactive="false"
        />
        <ProjectCard
          v-for="(item, index) in group.projects"
          :key="item.code"
          :record="item"
          :selected="item.code === selected"
          :style="{
            position: 'absolute',
            left: group.layout.cards[index].x + 'px',
            top: group.layout.cards[index].y + 'px',
            width: group.layout.cardWidth + 'px'
          }"
          @selected="choose"
        />
      </section>
      <p v-if="!groups.length" class="muted project-empty">
        {{ t('No projects match the current filters') }}
      </p>
    </div>
  </div>
</template>
<style>
.project-chooser.frame-project-chooser {
  width: var(--project-popup-width);
  height: var(--project-popup-height);
  border: 0;
}
.frame-project-chooser .project-header {
  position: relative;
  flex: none;
}
.frame-project-chooser .project-header > .frame-view {
  pointer-events: none;
}
.frame-project-chooser .project-close {
  position: absolute;
  right: 8px;
  top: 8px;
  width: 44px;
  height: 44px;
}
.frame-project-chooser .project-filters {
  position: absolute;
  bottom: 9px;
  left: 20px;
  right: 20px;
  padding: 0;
  border: 0;
  min-height: 30px;
  gap: 12px;
}
.frame-project-chooser .project-categories {
  margin-right: 12px;
  margin-bottom: 12px;
  padding: 0 0 0 12px;
  scrollbar-gutter: stable;
}
.frame-project-chooser .project-categories > section {
  position: relative;
  margin-bottom: 4px;
}
.frame-project-chooser.project-catalog-inline {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 600px;
  max-height: none;
  opacity: 1;
  transform: none;
  box-shadow: none;
}
</style>

<style>
.frame-project-chooser .project-filters .app-checkbox {
  padding-inline: var(--project-filter-padding);
}
</style>

<style>
.frame-project-chooser .project-category-heading {
  height: 42px;
}
</style>
