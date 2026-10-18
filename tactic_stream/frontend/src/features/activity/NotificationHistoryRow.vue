<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { t } from '../../i18n.js';
import { linkifyPlainText, activateRichLink } from '../../controls/richText.js';
import { browserLink } from '../workspace/links.js';
import { timestampLabel, timestampFullLabel } from './activity.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/notifications.ui.mjs';
const props = defineProps({ record: Object });
const emit = defineEmits(['open-link']);
const root = ref(null),
  width = ref(400),
  heights = ref({}),
  hovered = ref(false);
const model = computed(() => ({
  ...props.record,
  time: timestampLabel(props.record.timestamp, new Date()),
  hovered: hovered.value
}));
const scene = computed(() =>
  UI.row(model.value, width.value, heights.value, appearance.language)
);
let observer;
const port = {
  props: { frameNode: Object },
  setup(port, { attrs }) {
    const element = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const part = port.frameNode.view,
          height = element.value.getBoundingClientRect().height;
        if (height > 0 && heights.value[part] !== height)
          heights.value = { ...heights.value, [part]: height };
      });
      resize.observe(element.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () => {
      const part = port.frameNode.view,
        row = props.record;
      const content =
        part === 'time'
          ? h(
              'time',
              {
                ref: element,
                datetime: row.timestamp,
                title: timestampFullLabel(row.timestamp),
                style: {
                  display: 'block',
                  fontSize: '11px',
                  lineHeight: '15px',
                  textAlign: width.value >= 620 ? 'right' : 'left',
                  color: 'var(--muted)'
                }
              },
              model.value.time
            )
          : h(part === 'message' ? 'strong' : 'p', {
              ref: element,
              style: {
                display: 'block',
                margin: 0,
                fontSize: part === 'message' ? '14px' : '12px',
                lineHeight: part === 'message' ? '19px' : '16px',
                fontWeight: part === 'message' ? 600 : 400,
                color:
                  part === 'message' ? 'var(--on-surface)' : 'var(--muted)',
                overflowWrap: 'anywhere'
              },
              innerHTML: linkifyPlainText(
                row.sourceType ? row[part] : t(row[part]),
                browserLink
              ),
              onClick: (event) =>
                activateRichLink(event, (value) => emit('open-link', value))
            });
      return h('div', attrs, [content]);
    };
  }
};
const views = Object.fromEntries(
  ['message', 'time', 'detail'].map((name) => [
    name,
    { nodeProps: true, component: port }
  ])
);
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <article
    ref="root"
    class="system-activity-event"
    :data-kind="record.kind"
    :data-group="record.group"
    :style="{ height: scene.height + 'px' }"
    @mouseenter="hovered = true"
    @mouseleave="hovered = false"
  >
    <FrameView :scene="scene" :views="views" />
  </article>
</template>
<style>
.system-activity-event {
  position: relative;
  flex: none;
  min-width: 0;
  margin: 0 0 6px;
}
.system-activity-event strong,
.system-activity-event p,
.system-activity-event time {
  user-select: text;
}
</style>
