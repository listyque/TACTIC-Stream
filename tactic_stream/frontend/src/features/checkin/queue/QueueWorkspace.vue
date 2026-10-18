<script setup>
import { computed, ref, onMounted, onBeforeUnmount, markRaw } from 'vue';
import FrameView from '../../../frame/FrameView.vue';
import FrameProgress from '../../../frame/controls/display/FrameProgress.vue';
import DescriptionSurface from '../../objects/DescriptionSurface.vue';
import QueuePreview from './QueuePreview.vue';
import AppMenu from '../../../controls/AppMenu.vue';
import AppButton from '../../../controls/AppButton.vue';
import { observeFrameSizes } from '../../../frame/resize.js';
import { appearance } from '../../../appearance.js';
import * as UI from '../../../../../src/tactic_stream/shared_ui/features/files/queue/queue.ui.mjs';

const props = defineProps({
  model: Object,
  operations: Array,
  files: Array,
  previewFiles: Object
});
const emit = defineEmits(['event', 'resize']);
const host = ref(null),
  presenter = ref(null),
  menu = ref(null),
  menuAnchor = ref(null),
  menuType = ref('send'),
  menuIndex = ref(-1),
  menuKey = ref(''),
  viewport = ref({ width: 1000, height: 700 });
const scene = computed(() =>
  UI.describe(
    props.model,
    viewport.value.width,
    viewport.value.height,
    appearance.language
  )
);
const naming = computed(() =>
  UI.namingRows(props.model.record || {}, appearance.language)
);
const models = computed(() => ({
  operations: props.operations,
  files: props.files,
  naming: naming.value
}));
const previewComponent = markRaw(QueuePreview),
  descriptionComponent = markRaw(DescriptionSurface),
  progressComponent = markRaw(FrameProgress);
const views = computed(() => ({
  preview: {
    component: previewComponent,
    nodeProps: true,
    props: { files: props.previewFiles }
  },
  progress: { component: progressComponent, nodeProps: true },
  description: {
    component: descriptionComponent,
    props: {
      model: {
        managed: false,
        compact: true,
        enabled: !props.model.busy && !!props.model.record?.canDescription
      },
      text:
        props.model.descriptionDraft == null
          ? props.model.record?.description || ''
          : props.model.descriptionDraft,
      html: '',
      onValue: (value) => emit('event', { type: 'descriptionDraft', value }),
      onFinished: (value) => emit('event', { type: 'descriptionCommit', value })
    }
  }
}));
const actions = computed(() =>
  menuType.value === 'preview'
    ? UI.previewActions(props.model)
    : menuType.value === 'operation'
      ? UI.operationActions(
          props.model,
          props.operations.find(
            (record) => record.operationId === menuKey.value
          ) || {}
        )
      : UI.sendActions(props.model)
);
function describeRow(list, record, index) {
  if (list.source === 'operations')
    return UI.operationRow(
      props.model,
      record,
      index,
      list.width - 16,
      appearance.language
    );
  if (list.source === 'naming') return UI.namingRow(record, list.width - 16);
  return UI.sourceRow(
    props.model,
    record,
    list.width - 16,
    appearance.language
  );
}
function dispatch(action, source) {
  if (!['previewMenu', 'sendMenu', 'operationMenu'].includes(action.type)) {
    emit('event', action, source);
    return;
  }
  const kind =
    action.type === 'previewMenu'
      ? 'preview'
      : action.type === 'operationMenu'
        ? 'operation'
        : 'send';
  if (
    menu.value.open &&
    kind === menuType.value &&
    source === menuAnchor.value &&
    !action.value
  ) {
    menu.value.close(true);
    return;
  }
  menuType.value = kind;
  menuIndex.value = action.index ?? -1;
  menuKey.value = action.key || props.model.record?.operationId || '';
  menuAnchor.value = source;
  if (action.value) {
    const rect = source.getBoundingClientRect();
    menu.value.openAt({
      target: source,
      clientX: rect.x + action.value.x,
      clientY: rect.y + action.value.y
    });
  } else menu.value.openAt({ target: source });
}
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    const box = entries.at(-1).contentRect;
    if (box.width <= 0 || box.height <= 0) return;
    viewport.value = { width: box.width, height: box.height };
    emit('resize', viewport.value);
  });
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
defineExpose({
  element: () => host.value,
  focusControl: (id) => presenter.value?.focusControl(id),
  focusOperation: (index, id) =>
    presenter.value?.focusListRow(
      'commitQueueRows',
      index,
      'commitQueueSelect_' + id
    )
});
</script>
<template>
  <div ref="host" class="commit-queue-workspace" :aria-busy="model.busy">
    <FrameView
      ref="presenter"
      :scene="scene"
      :models="models"
      :views="views"
      :describe-row="describeRow"
      @event="dispatch"
    />
    <AppMenu
      ref="menu"
      class="commit-queue-action-menu"
      external-trigger
      overlay
      :anchor="menuAnchor"
      :label="
        menuType === 'preview'
          ? 'Preview actions'
          : menuType === 'operation'
            ? 'Operation actions'
            : 'More send actions'
      "
    >
      <template v-for="(action, index) in actions" :key="index">
        <hr v-if="action.separator" />
        <AppButton
          v-else
          :label="action.title"
          :icon="action.icon"
          :disabled="action.enabled === false"
          @click="
            emit('event', {
              type: 'menuCommand',
              menu: menuType,
              command: action.command,
              key: menuKey,
              index: menuIndex
            })
          "
        />
      </template>
    </AppMenu>
  </div>
</template>
<style>
.commit-queue-workspace {
  position: relative;
  min-width: 0;
  min-height: 0;
  width: 100%;
  height: 100%;
  flex: 1;
}
</style>
