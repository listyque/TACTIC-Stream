<script setup>
import { computed, ref } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/table/services.ui.mjs';
import { droppedKeys } from '../../../../src/tactic_stream/shared_ui/features/table/drop.ui.mjs';
import { onMounted, onBeforeUnmount } from 'vue';

const props = defineProps({
  cell: Object,
  height: Number,
  editable: Boolean,
  nestedState: Object
});
const emit = defineEmits(['action']);
const host = ref(null),
  width = ref(160),
  expanded = ref({});
let observer;
const scene = computed(() =>
  UI.describe(
    props.cell || {},
    width.value,
    props.height,
    appearance.language,
    props.editable,
    { ...expanded.value, __nested: props.nestedState },
    location.origin
  )
);
onMounted(() => {
  observer = observeFrameSizes(
    (entries) => (width.value = entries[0].contentRect.width)
  );
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function activate(action, value) {
  if (action.type === 'parallel-toggle') {
    expanded.value = {
      ...expanded.value,
      [action.identity]: !expanded.value[action.identity]
    };
  } else {
    try {
      emit(
        'action',
        action.name,
        {
          ...props.cell,
          nestedTable: action.nestedTable || props.cell.nestedTable,
          href: action.href,
          displayOptions: {
            ...props.cell.displayOptions,
            ...(action.javascript ? { cbjs_action: action.javascript } : {})
          },
          actionView: action.view,
          actionProcess: action.process,
          targetSearchKey: action.targetSearchKey || props.cell.targetSearchKey,
          dropKeys:
            action.name === 'drop-links'
              ? droppedKeys(value, props.cell.acceptedType)
              : [],
          actionTaskKey: action.taskKey,
          actionDay: action.day,
          actionTaskCode: action.taskCode
        },
        host.value
      );
    } catch (error) {
      emit('action', 'error', { error: error.message }, host.value);
    }
  }
}
</script>

<template>
  <div ref="host" class="table-service-cell">
    <FrameView
      :scene="scene"
      :style="{ height: height + 'px' }"
      @event="activate"
    />
  </div>
</template>

<style scoped>
.table-service-cell {
  display: flex;
  align-items: center;
  width: 100%;
  min-width: 0;
  height: 100%;
}
</style>
