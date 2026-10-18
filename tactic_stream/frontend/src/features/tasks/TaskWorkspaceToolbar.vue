<script setup>
import { appearance } from '../../appearance.js';
import {
  metrics,
  fontFamily,
  textStyles
} from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { computed, markRaw, h, ref, nextTick } from 'vue';
import TaskWorkspacePart from './TaskWorkspacePart.vue';
import TaskWorkspaceSurfaceSwitcher from './TaskWorkspaceSurfaceSwitcher.vue';
import AppSearchField from '../../controls/AppSearchField.vue';
import { t } from '../../i18n.js';
const props = defineProps({ model: Object });
const emit = defineEmits(['event']);
const search = ref(null);
const paintModel = computed(() => ({
  ...props.model,
  controlHeight: metrics(appearance.theme).controlHeight,
  scopeTextWidth: qtLabelTextWidth(
    props.model.scopeLabel || '',
    `600 ${textStyles.body}px "${fontFamily}"`
  )
}));
const searchPort = markRaw({
  setup(_, { attrs }) {
    return () =>
      h(AppSearchField, {
        ...attrs,
        ref: search,
        modelValue: props.model.text,
        label: 'Search tasks',
        placeholder: t('Search tasks'),
        disabled: props.model.blocked && !props.model.loading,
        'onUpdate:modelValue': (value) =>
          emit('event', { type: 'search-input', value }),
        onSearch: () => emit('event', { type: 'search-submit' }),
        onDismiss: () => emit('event', { type: 'search-dismiss' })
      });
  }
});
const surfacePort = markRaw(TaskWorkspaceSurfaceSwitcher);
const views = computed(() => ({
  search: { component: searchPort },
  surfaces: {
    component: surfacePort,
    props: {
      value: props.model.surface,
      disabled: props.model.blocked && !props.model.loading,
      onChange: (value) => emit('event', { type: 'surface', value })
    }
  }
}));
async function focusSearch() {
  await nextTick();
  search.value?.focus();
}
defineExpose({ focusSearch });
</script>
<template>
  <TaskWorkspacePart
    class="task-workspace-toolbar"
    part="toolbar"
    :model="paintModel"
    :views="views"
    @event="(action, source) => emit('event', action, source)"
  />
</template>
<style>
.task-workspace-menus {
  height: 0;
  flex: none;
}
.task-manager-toolbar.task-workspace-toolbar {
  display: block;
  height: 58px;
  min-height: 58px;
  padding: 0;
}
@media (max-width: 700px) {
  .task-manager-toolbar.task-workspace-toolbar {
    height: 40px;
    min-height: 40px;
  }
}
</style>
