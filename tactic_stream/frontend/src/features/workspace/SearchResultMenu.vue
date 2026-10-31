<script setup>
import { computed, ref, nextTick, watch } from 'vue';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import AppMenu from '../../controls/AppMenu.vue';
import AppIcon from '../../controls/AppIcon.vue';
import ActionRows from '../../controls/ActionRows.vue';
import FrameView from '../../frame/FrameView.vue';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/menus.ui.mjs';
const props = defineProps({
  kind: String,
  model: Object,
  label: String,
  icon: String,
  boundary: Object,
  iconOnly: Boolean,
  toolbarWidth: { type: Number, default: 0 },
  tabsWidth: { type: Number, default: 0 },
  historyWidth: { type: Number, default: 0 }
});
const emit = defineEmits(['command', 'opening']);
const menu = ref(null),
  editor = ref(null),
  anchor = ref(null),
  column = ref(''),
  direction = ref('asc');
const inlineViews = computed(
  () =>
    props.kind === 'view' &&
    UI.inlineViews(props.toolbarWidth, props.tabsWidth, props.historyWidth)
);
const picker = computed(() =>
  UI.describeViewPicker(props.model, appearance.language)
);
const extraView = computed(
  () => !UI.views.slice(0, 3).some((view) => view.value === props.model.mode)
);
const triggerIcon = computed(() =>
  inlineViews.value && !extraView.value ? 'expand-more' : props.icon
);
watch(inlineViews, () => menu.value?.close(false));
function selectView(action) {
  if (action.type === 'view' && !props.model.busy) {
    menu.value?.close(false);
    emit('command', action.value);
  }
}
const actions = computed(() =>
  props.kind === 'filters'
    ? UI.filterActions(props.model)
    : props.kind === 'sort'
      ? UI.sortActions(props.model)
      : props.kind === 'group'
        ? UI.groupActions(props.model)
        : UI.viewActions(props.model.mode, props.model.busy)
);
const scene = computed(() =>
  UI.sortColumn(
    {
      column: column.value,
      direction: direction.value,
      columns: props.model.columns,
      busy: props.model.busy
    },
    256,
    appearance.language
  )
);
function opened(event) {
  if (event.target === event.currentTarget && event.target.open)
    emit('opening');
}
async function choose(command) {
  if (props.kind === 'sort' && command === 'column') {
    anchor.value = menu.value.$el.querySelector('summary');
    column.value = props.model.column || props.model.columns?.[0]?.value || '';
    direction.value = props.model.direction || 'asc';
    menu.value.close(false);
    await nextTick();
    const bounds = anchor.value.getBoundingClientRect();
    editor.value.openAt({
      clientX: bounds.left,
      clientY: bounds.top,
      target: anchor.value
    });
  } else {
    menu.value.close(true);
    emit('command', command);
  }
}
function edit(action) {
  if (action.type === 'column') column.value = action.value;
  else if (action.type === 'direction')
    direction.value = direction.value === 'asc' ? 'desc' : 'asc';
  else if (action.type === 'apply' && column.value) {
    editor.value.close(true);
    emit('command', 'column:' + column.value + ':' + direction.value);
  }
}
function close() {
  menu.value.close(true);
  editor.value?.close(true);
}
defineExpose({ close });
</script>
<template>
  <FrameView
    v-if="inlineViews"
    :scene="picker"
    class="result-view-picker"
    :style="{
      width: UI.viewPicker.width + 'px',
      height: UI.viewPicker.height + 'px'
    }"
    @event="selectView"
  />
  <AppMenu
    ref="menu"
    :overlay="kind === 'filters'"
    :align-start="kind === 'filters'"
    :label="label"
    :icon="triggerIcon"
    :boundary="boundary"
    :width="kind === 'filters' ? 300 : 280"
    @toggle="opened"
  >
    <template #trigger
      ><AppIcon
        :name="triggerIcon"
        :style="
          inlineViews && extraView ? { color: 'var(--primary)' } : undefined
        "
      /><span v-if="!iconOnly" class="result-action-label">{{
        t(label)
      }}</span></template
    >
    <ActionRows :actions="actions" @triggered="choose" />
  </AppMenu>
  <AppMenu
    v-if="kind === 'sort'"
    ref="editor"
    external-trigger
    frame-composition
    overlay
    :boundary="boundary"
    :anchor="anchor"
    :width="280"
    label="Sort by column"
    :close-on-select="false"
  >
    <FrameView :scene="scene" style="height: 156px" @event="edit" />
  </AppMenu>
</template>
<style>
.result-view-picker {
  flex: none;
  align-self: center;
}
</style>
