<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppProgress from '../../controls/AppProgress.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import { appearance } from '../../appearance.js';
import { mobile } from '../../mobile.js';
import { t } from '../../i18n.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/activity/toast.ui.mjs';
const props = defineProps({ row: Object });
const emit = defineEmits(['action']);
const root = ref(null),
  width = ref(390),
  heights = ref({});
let observer;
const scene = computed(() =>
  UI.describe(
    {
      ...props.row,
      sourceType:
        props.row.sourceType === 'messages' ? 'message' : props.row.sourceType
    },
    width.value,
    heights.value,
    appearance.language,
    mobile.value
  )
);
const port = {
  props: { frameNode: Object },
  setup(port, { attrs }) {
    const text = ref(null);
    let resize;
    onMounted(() => {
      if (!text.value) return;
      resize = observeFrameSizes(() => {
        const part = port.frameNode.view,
          height = text.value.getBoundingClientRect().height;
        if (height > 0 && heights.value[part] !== height)
          heights.value = { ...heights.value, [part]: height };
      });
      resize.observe(text.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () => {
      const part = port.frameNode.view;
      if (part === 'progress')
        return h('div', attrs, [
          h(AppProgress, {
            label: props.row.message,
            value: props.row.progress < 0 ? undefined : props.row.progress,
            style: { position: 'absolute', top: '4px' }
          })
        ]);
      const value =
        part === 'message'
          ? props.row.sourceType
            ? props.row.message
            : t(props.row.message)
          : part === 'error'
            ? t(props.row.replyError)
            : props.row.detail;
      return h('div', attrs, [
        h(
          'div',
          {
            ref: text,
            class: 'notification-' + (part === 'error' ? 'reply-error' : part),
            style: {
              fontSize:
                part === 'message' ? (mobile.value ? '12px' : '13px') : '11px',
              lineHeight:
                part === 'message' ? (mobile.value ? '16px' : '18px') : '15px',
              fontWeight: part === 'message' ? 600 : 400,
              color:
                part === 'error'
                  ? 'var(--error)'
                  : part === 'detail'
                    ? 'var(--muted)'
                    : 'var(--on-surface)',
              display: part === 'detail' ? '-webkit-box' : 'block',
              WebkitBoxOrient: 'vertical',
              WebkitLineClamp: part === 'detail' ? 2 : undefined,
              maxHeight:
                mobile.value &&
                part === 'message' &&
                ['error', 'warning'].includes(props.row.kind)
                  ? '64px'
                  : undefined,
              overflow:
                part === 'detail'
                  ? 'hidden'
                  : mobile.value &&
                      part === 'message' &&
                      ['error', 'warning'].includes(props.row.kind)
                    ? 'auto'
                    : undefined,
              overflowWrap: 'anywhere'
            }
          },
          value
        )
      ]);
    };
  }
};
const views = Object.fromEntries(
  ['message', 'detail', 'error', 'progress'].map((name) => [
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
    class="notification-card"
    :data-notification-id="row.notificationId"
    :data-kind="row.kind"
    :data-source="row.sourceType || ''"
    :data-dismissible="row.dismissible"
    :role="['error', 'warning'].includes(row.kind) ? 'alert' : 'status'"
    :style="{ height: scene.height + 'px', borderRadius: scene.radius + 'px' }"
  >
    <FrameView
      :scene="scene"
      :views="views"
      @event="(event) => emit('action', event)"
    />
  </article>
</template>
<style>
.notification-card {
  position: relative;
  flex: none;
  min-width: 0;
  background: var(--surface-high);
  box-shadow:
    inset 0 0 0 1px var(--outline),
    2px 5px 12px var(--shadow-color);
}
.notification-card > .frame-view {
  height: 100%;
}
</style>
