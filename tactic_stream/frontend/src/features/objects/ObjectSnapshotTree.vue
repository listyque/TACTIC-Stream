<script setup>
import { computed, h, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/snapshot_tree.ui.mjs';
const props = defineProps({ metrics: Object, groups: Array });
const emit = defineEmits(['snapshot', 'file']);
const host = ref(null),
  width = ref(0),
  expanded = ref({}),
  fileHeights = ref({});
const scene = computed(() =>
  UI.describe(
    {
      metrics: props.metrics,
      groups: props.groups,
      expanded: expanded.value,
      fileHeights: fileHeights.value
    },
    width.value,
    appearance.language
  )
);
let observer;
const views = {
  attachment: {
    nodeProps: true,
    component: {
      props: { frameNode: Object },
      setup(props, { attrs }) {
        const element = ref(null);
        let resize;
        onMounted(() => {
          resize = observeFrameSizes(() => {
            const height = element.value.scrollHeight,
              token = props.frameNode.record.token;
            if (height > 0 && fileHeights.value[token] !== height)
              fileHeights.value = { ...fileHeights.value, [token]: height };
          });
          resize.observe(element.value);
        });
        onBeforeUnmount(() => resize?.disconnect());
        return () => {
          const record = props.frameNode.record;
          return h('div', { ...attrs }, [
            h('div', { ref: element }, [
              h(AttachmentCard, {
                title: record.title,
                extension: record.extension,
                previewUrl: record.previewUrl,
                sizeText: record.sizeText,
                local: !!record.exists,
                webPreview: false,
                activationLabel: 'Open attachment',
                onActivated: () => emit('file', record)
              })
            ])
          ]);
        };
      }
    }
  }
};
onMounted(() => {
  const measure = () => {
    width.value = host.value.clientWidth;
  };
  measure();
  observer = observeFrameSizes(measure);
  observer.observe(host.value);
});
onBeforeUnmount(() => observer?.disconnect());
function action(event) {
  if (event.type === 'expand')
    expanded.value = {
      ...expanded.value,
      [event.value]: !expanded.value[event.value]
    };
  else if (event.type === 'snapshot') emit('snapshot', event.key);
}
</script>
<template>
  <section
    ref="host"
    class="object-snapshot-tree"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" @event="action" />
  </section>
</template>
<style>
.object-snapshot-tree {
  width: 100%;
  min-width: 0;
  flex: none;
}
.object-snapshot-tree .attachment-card {
  width: 100%;
}
</style>
