<script setup>
import { computed, ref, markRaw, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import QuickFilterChip from '../../controls/display/QuickFilterChip.vue';
import { observeFrameSizes, frameContentWidth } from '../../frame/resize.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { appearance } from '../../appearance.js';
import {
  fontFamily,
  textStyles
} from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/tasks/filters.ui.mjs';
import { t } from '../../i18n.js';
const props = defineProps({
  filters: Object,
  quick: Object,
  facets: Object,
  busy: Boolean,
  active: Boolean,
  scope: String
});
const emit = defineEmits(['filter', 'quick', 'clear', 'clear-group']);
const host = ref(null),
  width = ref(0),
  advanced = ref(false);
const groups = computed(() =>
  UI.fromFacets(props.facets, props.quick, props.scope)
);
const scene = computed(() =>
  UI.describe(
    {
      groups: groups.value,
      filters: props.filters,
      busy: props.busy,
      active: props.active,
      advanced: advanced.value
    },
    width.value,
    appearance.language,
    (text) => qtLabelTextWidth(text, `600 ${textStyles.body}px "${fontFamily}"`)
  )
);
function event(action) {
  if (action.type === 'clear') emit('clear');
  else if (action.type === 'quick')
    emit('quick', action.group, action.value, action.checked);
  else if (action.type === 'clear-group') emit('clear-group', action.group);
  else if (action.type === 'advanced') advanced.value = !advanced.value;
  else if (action.type === 'filter') emit('filter', action.field, action.value);
}
const chip = markRaw({
  props: { frameNode: Object },
  setup(port) {
    return () =>
      h(QuickFilterChip, {
        text: port.frameNode.record.text,
        checked: port.frameNode.record.selected,
        accent: port.frameNode.record.accent,
        showAccentMarker: port.frameNode.marker,
        subtle: port.frameNode.marker,
        disabled: !port.frameNode.enabled,
        style: { width: '100%', height: '100%' },
        onClick: () => event(port.frameNode.action)
      });
  }
});
const views = { chip: { component: chip, nodeProps: true } };
let observer;
onMounted(() => {
  const measure = () => {
    width.value = frameContentWidth(host.value);
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="host"
    class="task-filter-fields"
    role="group"
    :aria-label="t('Quick filters')"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="event" />
  </div>
</template>
<style>
.task-filter-fields {
  position: relative;
  display: block;
  min-width: 0;
  width: 100%;
}
</style>
