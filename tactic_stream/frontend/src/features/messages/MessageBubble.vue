<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import EmojiPicker from '../../controls/EmojiPicker.vue';
import ItemPreview from '../../controls/ItemPreview.vue';
import MessageHeader from './MessageHeader.vue';
import MessageBody from './MessageBody.vue';
import * as State from '../../../../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs';
import { observeFrameSizes } from '../../frame/resize.js';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import { contextActions as vContextActions } from '../../controls/contextActions.js';
import { appearance } from '../../appearance.js';
import {
  initials,
  messageId,
  messageAttachments,
  attachmentName,
  bubbleContour
} from './messages.js';
const props = defineProps({
  row: Object,
  login: String,
  user: Object,
  users: Array,
  selected: Boolean,
  selectionMode: Boolean,
  canEdit: Boolean,
  permissions: Object,
  busy: Boolean,
  pinned: Boolean,
  loadFile: Function,
  fileActions: Object,
  previews: Object,
  now: Number
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
const bubble = ref(null),
  menu = ref(null),
  reactionPicker = ref(null),
  menuAnchor = ref(null),
  rowElement = ref(null),
  rowWidth = ref(500),
  hovered = ref(false),
  focused = ref(false),
  size = ref({ width: 0, height: 0, corner: 14 });
const geometry = computed(() =>
  State.bubbleGeometry(
    rowWidth.value,
    0,
    0,
    {
      last: props.row.groupLast,
      own: props.row.login === props.login,
      media: media.value
    },
    appearance.theme
  )
);
const inset = computed(() =>
  props.row.groupLast ? geometry.value.tail + 2 : 2
);
const contour = computed(() =>
  bubbleContour(
    size.value.width,
    size.value.height,
    size.value.corner,
    props.row.groupLast,
    geometry.value.tail
  )
);
const media = computed(() =>
  messageAttachments(props.row).some((snapshot) =>
    /^(png|jpe?g|webp|gif|bmp|tiff?|tga|exr|hdr|svg|heic|avif)$/i.test(
      attachmentName(snapshot).split('.').at(-1)
    )
  )
);
let observer;
function measure() {
  if (rowElement.value?.clientWidth > 0)
    rowWidth.value = rowElement.value.clientWidth;
  if (bubble.value) {
    const box = bubble.value.getBoundingClientRect(),
      corner = parseFloat(getComputedStyle(bubble.value).borderTopLeftRadius);
    if (
      box.width &&
      box.height &&
      (box.width !== size.value.width ||
        box.height !== size.value.height ||
        corner !== size.value.corner)
    )
      size.value = { width: box.width, height: box.height, corner };
  }
}
onMounted(() => {
  observer = observeFrameSizes(measure);
  observer.observe(bubble.value);
  observer.observe(rowElement.value);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());
watch(() => appearance.theme, measure, { flush: 'post' });
const action = (name, row) => emit('action', name, row);
function selectMessage(event) {
  if (
    props.selectionMode &&
    !event.target.closest(
      'button, a, input, textarea, select, [role=button], .workspace-menu'
    )
  ) {
    event.preventDefault();
    event.stopPropagation();
    action('select', props.row);
  }
}
function openMenu(event) {
  menuAnchor.value = null;
  menu.value.openAt(event);
}
function headerAction(event, source) {
  if (event.type === 'menu') {
    if (menu.value.open) menu.value.close(true);
    else {
      menuAnchor.value = source;
      menu.value.openAt({ target: source });
    }
  } else if (event.type === 'reaction') reactionPicker.value.openFor(source);
  else if (event.type === 'profile') action('profile', props.row.login);
  else action(event.type, props.row);
}
</script>
<template>
  <article
    ref="rowElement"
    v-context-actions="openMenu"
    @pointerenter="hovered = true"
    @pointerleave="hovered = false"
    @focusin="focused = true"
    @focusout="focused = false"
    :style="{
      '--avatar-extent': geometry.avatar + 'px',
      '--outer-margin': geometry.margin + 'px',
      '--bubble-padding': geometry.padding + 'px',
      '--bubble-minimum': (rowWidth < 380 ? 104 : 116) + 'px',
      '--bubble-maximum': geometry.maximum + 'px'
    }"
    class="message-row"
    :class="{
      outgoing: row.login === login,
      'group-first': row.groupFirst,
      'group-last': row.groupLast,
      'forward-selected': selected,
      'media-attachments': media
    }"
    :data-message-id="messageId(row)"
  >
    <AppButton
      v-if="row.groupLast"
      class="message-author-action"
      :aria-label="t('Open profile for {name}', { name: row.login })"
      @click="action('profile', row.login)"
      ><ItemPreview
        class="message-author"
        :source="user?.avatarUrl"
        :fallback-text="user?.initials || initials(row.login)"
        :accent="user?.avatarColor || 'var(--primary)'"
        :preview-size="geometry.avatar"
        round
        outlined
    /></AppButton>
    <div
      ref="bubble"
      class="message-bubble"
      :style="{ '--sender-color': user?.avatarColor || 'var(--primary)' }"
      @click.capture="selectMessage"
    >
      <svg
        v-if="size.width && size.height"
        class="message-contour"
        :viewBox="`0 0 ${size.width + inset * 2} ${size.height + 4}`"
        :style="{ left: -inset + 'px', width: `calc(100% + ${inset * 2}px)` }"
        aria-hidden="true"
        focusable="false"
      >
        <path :d="contour" />
      </svg>
      <MessageHeader
        :row="row"
        :user="user"
        :login="login"
        :busy="busy"
        :pinned="pinned"
        :selected="selected"
        :selection-mode="selectionMode"
        :permissions="permissions"
        :hovered="hovered"
        :focused="focused"
        :touch="mobile"
        :now="now"
        :padding="geometry.padding"
        :maximum-width="geometry.maximum - geometry.padding * 2"
        @event="headerAction"
      />
      <div class="message-frame-menus">
        <AppMenu
          ref="menu"
          class="message-actions message-frame-menu"
          external-trigger
          :anchor="menuAnchor"
          label="Message actions"
          overlay
        >
          <EmojiPicker
            v-if="mobile && permissions.reaction"
            text-trigger
            label="Add reaction"
            :disabled="busy"
            @selected="
              menu.close();
              emit('reaction', row, $event);
            "
          />
          <AppButton
            label="Reply"
            icon="MDI_REPLY"
            :disabled="!permissions.send"
            @click="action('reply', row)"
          />
          <AppButton
            label="Forward"
            icon="MDI_SHARE"
            :disabled="!permissions.forward"
            @click="action('forward', row)"
          />
          <AppButton
            :label="selected ? 'Deselect message' : 'Select message'"
            icon="MDI_CHECKBOX_MARKED_OUTLINE"
            @click="action('select', row)"
          />
          <AppButton
            label="Copy text"
            icon="MDI_CONTENT_COPY"
            @click="action('copy', row)"
          /><AppButton
            label="Copy sKey"
            icon="MDI_LINK"
            @click="action('skey', row)"
          />
          <AppButton
            :label="pinned ? 'Unpin message' : 'Pin message'"
            icon="pin"
            :disabled="!permissions.pin || busy"
            @click="action('pin', row)"
          />
          <AppButton
            v-if="row.__edit_history__?.length"
            label="Edit history"
            icon="MDI_HISTORY"
            @click="action('history', row)"
          />
          <AppButton
            label="Edit message"
            icon="MDI_PENCIL"
            :disabled="!canEdit || busy"
            @click="action('edit', row)"
          />
          <AppButton
            label="Delete message"
            icon="MDI_DELETE"
            destructive
            :disabled="!canEdit || busy || !permissions['delete-message']"
            @click="action('delete-message', row)"
          /> </AppMenu
        ><EmojiPicker
          ref="reactionPicker"
          external-trigger
          label="Add reaction"
          :disabled="busy"
          @selected="emit('reaction', row, $event)"
        />
      </div>
      <MessageBody
        :maximum-width="geometry.maximum - geometry.padding * 2"
        :row="row"
        :login="login"
        :users="users"
        :busy="busy"
        :permissions="permissions"
        :load-file="loadFile"
        :file-actions="fileActions"
        :previews="previews"
        :now="now"
        @action="(name, value) => emit('action', name, value)"
        @attachment-action="
          (name, value) => emit('attachment-action', name, value)
        "
        @reaction="(row, value) => emit('reaction', row, value)"
        @link="(value) => emit('link', value)"
        @jump="(value) => emit('jump', value)"
        @session-expired="emit('session-expired')"
        @preview-retry="(value) => emit('preview-retry', value)"
        @copy-link="(value) => emit('copy-link', value)"
      />
    </div>
  </article>
</template>

<style>
.message-frame-menus {
  position: absolute;
  width: 0;
  height: 0;
}
.message-bubble .message-frame-menu {
  opacity: 1;
  pointer-events: auto;
}
.message-bubble .message-frame-body {
  flex: none;
}
.message-bubble {
  gap: 6px;
}
.message-row.media-attachments .message-bubble {
  --bubble-maximum: inherit;
}
</style>
