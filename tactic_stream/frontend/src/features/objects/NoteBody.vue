<script setup>
import { computed, ref, h, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppIcon from '../../controls/AppIcon.vue';
import AttachmentCard from '../../controls/AttachmentCard.vue';
import ResponsiveFlow from '../../controls/ResponsiveFlow.vue';
import SKeyPreviewCard from './SKeyPreviewCard.vue';
import { observeFrameSizes } from '../../frame/resize.js';
import {
  linkifyPlainText,
  activateRichLink,
  extractSkeys,
  withoutSkeys
} from '../../controls/richText.js';
import { emojiCount } from '../messages/messages.js';
import { skeyPlaceholder } from './skeyPreviews.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/objects/note.ui.mjs';
const props = defineProps({
  note: Object,
  files: Array,
  previews: Object,
  statusColor: String
});
const emit = defineEmits(['link', 'retry', 'copy', 'file']);
const host = ref(null),
  width = ref(0),
  heights = ref({});
const keys = computed(() => extractSkeys(props.note.body));
const text = computed(() => withoutSkeys(props.note.body));
const scene = computed(() =>
  UI.body(
    {
      status: props.note.entry_type === 'status',
      statusText: props.note.after,
      statusColor: props.statusColor,
      text: props.note.entry_type !== 'status' && !!text.value,
      previews: !!keys.value.length,
      attachments: !!props.files?.length
    },
    width.value,
    heights.value
  )
);
let observer;
const port = {
  props: { frameNode: Object },
  setup(port, { attrs }) {
    const element = ref(null);
    let resize;
    onMounted(() => {
      resize = observeFrameSizes(() => {
        const part = port.frameNode.view;
        if (!element.value) return;
        const height = Math.round(element.value.getBoundingClientRect().height);
        if (height > 0 && Math.abs((heights.value[part] || 0) - height) > 1)
          heights.value = { ...heights.value, [part]: height };
      });
      resize.observe(element.value);
    });
    onBeforeUnmount(() => resize?.disconnect());
    return () => {
      let content;
      if (port.frameNode.view === 'status')
        content = h(
          'div',
          { style: { display: 'flex', gap: '8px', alignItems: 'center' } },
          [
            h(AppIcon, {
              name: 'status',
              style: { fontSize: '22px', color: props.statusColor }
            }),
            h(
              'span',
              {
                style: {
                  minWidth: 0,
                  flex: 1,
                  fontWeight: 500,
                  overflowWrap: 'anywhere'
                }
              },
              props.note.after || '—'
            )
          ]
        );
      else if (port.frameNode.view === 'text') {
        const count = emojiCount(text.value);
        content = h('div', {
          class: 'note-body',
          style: {
            margin: 0,
            fontSize: count ? 'var(--text-emoji-' + count + ')' : undefined,
            fontFamily: count ? "'Segoe UI Emoji',sans-serif" : undefined,
            lineHeight: count ? '1.125' : undefined,
            padding: count ? '5px 0' : undefined
          },
          innerHTML: linkifyPlainText(text.value),
          onClick: (event) =>
            activateRichLink(event, (key) => emit('link', key))
        });
      } else if (port.frameNode.view === 'previews')
        content = keys.value.map((key) =>
          h(SKeyPreviewCard, {
            key,
            preview: props.previews?.[key] || skeyPlaceholder(key),
            previews: props.previews,
            onOpen: (key) => emit('link', key),
            onRetry: (key) => emit('retry', key),
            onCopy: (key) => emit('copy', key)
          })
        );
      else
        content = h(
          ResponsiveFlow,
          {
            minimumCellWidth: UI.bodyMetrics.minimumCellWidth,
            maximumColumns: UI.bodyMetrics.maximumColumns,
            spacing: UI.bodyMetrics.gap
          },
          () =>
            props.files.map((file) =>
              h(AttachmentCard, {
                key: file.href,
                'data-flow-full': file.previewUrl ? '' : undefined,
                title: file.filename,
                extension: file.extension,
                previewUrl: file.previewUrl,
                sizeText: file.sizeText,
                webPreview: false,
                activationLabel: 'File preview',
                onActivated: () => emit('file', file)
              })
            )
        );
      return h('div', attrs, [
        h(
          'div',
          {
            ref: element,
            class: 'note-body-port',
            style: { display: 'grid', gap: UI.bodyMetrics.gap + 'px' }
          },
          content
        )
      ]);
    };
  }
};
const views = {
  status: { nodeProps: true, component: port },
  text: { nodeProps: true, component: port },
  previews: { nodeProps: true, component: port },
  attachments: { nodeProps: true, component: port }
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
</script>
<template>
  <div
    ref="host"
    class="note-body-surface"
    :style="{ height: scene.height + 'px' }"
  >
    <FrameView :scene="scene" :views="views" />
  </div>
</template>
<style>
.note-body-surface {
  position: relative;
  width: 100%;
  min-width: 0;
  flex: none;
}
.note-body-port .attachment-card {
  width: 100%;
}
.note-body-port .note-body {
  white-space: normal;
  overflow-wrap: anywhere;
  user-select: text;
}
.note-body-port .note-body a {
  color: var(--primary);
}
</style>
