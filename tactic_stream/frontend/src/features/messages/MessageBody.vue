<script setup>
import { computed, h, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../../frame/FrameView.vue';
import AppButton from '../../controls/AppButton.vue';
import ResponsiveFlow from '../../controls/ResponsiveFlow.vue';
import MessageReference from './MessageReference.vue';
import AttachmentItem from './AttachmentItem.vue';
import SKeyPreviewCard from '../objects/SKeyPreviewCard.vue';
import { skeyPlaceholder } from '../objects/skeyPreviews.js';
import {
  extractSkeys,
  withoutSkeys,
  linkifyPlainText,
  activateRichLink
} from '../../controls/richText.js';
import { observeFrameSizes } from '../../frame/resize.js';
import { messageAttachments, emojiCount } from './messages.js';
import { t } from '../../i18n.js';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/message.ui.mjs';
const props = defineProps({
  row: Object,
  login: String,
  users: Array,
  busy: Boolean,
  permissions: Object,
  loadFile: Function,
  fileActions: Object,
  previews: Object,
  now: Number,
  maximumWidth: Number
});
const emit = defineEmits([
  'action',
  'attachment-action',
  'reaction',
  'link',
  'jump',
  'session-expired',
  'preview-retry',
  'copy-link'
]);
const root = ref(null),
  width = ref(220),
  heights = ref({});
let observer;
const keys = computed(() => extractSkeys(props.row.message)),
  text = computed(() => withoutSkeys(props.row.message)),
  files = computed(() => messageAttachments(props.row)),
  stickers = computed(() => emojiCount(props.row.message));
const scene = computed(() =>
  UI.body(
    {
      reply: !!props.row.__reply__,
      forward: !!props.row.__forwarded_from__,
      previews: !!keys.value.length,
      attachments: !!files.value.length,
      text: !!text.value,
      reactions: !!Object.keys(props.row.__reactions__ || {}).length
    },
    width.value,
    heights.value
  )
);
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
      const part = port.frameNode.view;
      let content;
      if (part === 'reply')
        content = h(MessageReference, {
          reference: props.row.__reply__,
          users: props.users,
          onActivate: () => emit('jump', props.row.__reply__.messageId)
        });
      else if (part === 'forward')
        content = h(MessageReference, {
          reference: props.row.__forwarded_from__,
          users: props.users,
          forwarded: true,
          onActivate: () =>
            emit('action', 'original', props.row.__forwarded_from__)
        });
      else if (part === 'previews')
        content = h(
          'div',
          { class: 'message-skey-previews' },
          keys.value.map((key) =>
            h(SKeyPreviewCard, {
              key,
              preview: props.previews?.[key] || skeyPlaceholder(key),
              previews: props.previews,
              now: props.now,
              onOpen: (value) => emit('link', value),
              onRetry: (value) => emit('preview-retry', value),
              onCopy: (value) => emit('copy-link', value)
            })
          )
        );
      else if (part === 'attachments')
        content = h(
          ResponsiveFlow,
          {
            minimumCellWidth: UI.metrics.minimumCellWidth,
            preferredCellWidth: UI.metrics.preferredCellWidth,
            maximumColumns: UI.metrics.maximumColumns
          },
          () =>
            files.value.map((snapshot) =>
              h(AttachmentItem, {
                key: snapshot.code,
                snapshot,
                loadFile: props.loadFile,
                actionState: props.fileActions?.[snapshot.code],
                onOpen: (value) => emit('action', 'attachment', value),
                onAction: (name, value) =>
                  emit('attachment-action', name, value),
                onSessionExpired: () => emit('session-expired')
              })
            )
        );
      else if (part === 'text')
        content = h('div', {
          class: ['message-body', { 'emoji-only': stickers.value }],
          style: stickers.value
            ? { fontSize: 'var(--text-emoji-' + stickers.value + ')' }
            : undefined,
          innerHTML: linkifyPlainText(text.value),
          onClick: (event) =>
            activateRichLink(event, (value) => emit('link', value))
        });
      else
        content = h(
          'div',
          { class: 'message-reactions' },
          Object.entries(props.row.__reactions__ || {}).map(([emoji, actors]) =>
            h(
              AppButton,
              {
                key: emoji,
                tooltip: actors.join(', '),
                ariaLabel: t('React with {emoji}', { emoji }),
                tonal: actors.includes(props.login),
                disabled: props.busy || !props.permissions?.reaction,
                onClick: () => emit('reaction', props.row, emoji)
              },
              () => [
                emoji,
                actors.length > 1 ? h('small', actors.length) : null
              ]
            )
          )
        );
      return h('div', attrs, [
        h('div', { ref: element, class: 'message-body-port' }, [content])
      ]);
    };
  }
};
const views = Object.fromEntries(
  ['reply', 'forward', 'previews', 'attachments', 'text', 'reactions'].map(
    (name) => [name, { nodeProps: true, component: port }]
  )
);
onMounted(() => {
  const measure = () => {
    if (root.value.clientWidth > 0) width.value = root.value.clientWidth;
  };
  observer = observeFrameSizes(measure);
  observer.observe(root.value);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());
</script>
<template>
  <div
    ref="root"
    class="message-frame-body"
    :style="{
      height: scene.height + 'px',
      minWidth:
        Math.min(
          maximumWidth || 9999,
          Math.ceil(
            Math.max(
              0,
              ...text
                .split('\n')
                .map((line) => qtLabelTextWidth(line, '13px Segoe UI'))
            )
          ) + 2
        ) + 'px'
    }"
  >
    <FrameView :scene="scene" :views="views" />
  </div>
</template>
<style>
.message-frame-body {
  position: relative;
  flex: none;
  min-width: 0;
}
.message-body-port {
  min-width: 0;
  display: grid;
}
.message-frame-body .message-body {
  margin: 0;
}
</style>
