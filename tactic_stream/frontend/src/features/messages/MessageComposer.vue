<script setup>
import {
  ref,
  computed,
  watch,
  nextTick,
  onMounted,
  onBeforeUnmount,
  useId
} from 'vue';
import EmojiPicker from '../../controls/EmojiPicker.vue';
import AppButton from '../../controls/AppButton.vue';
import { t } from '../../i18n.js';
import { mobile } from '../../mobile.js';
import { observeFrameSizes } from '../../frame/resize.js';
import FrameView from '../../frame/FrameView.vue';
import * as Panels from '../../../../src/tactic_stream/shared_ui/features/messages/panels.ui.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/messages/composer.ui.mjs';
import * as State from '../../../../src/tactic_stream/shared_ui/features/messages/messaging.state.mjs';
const props = defineProps({
  modelValue: String,
  sending: Boolean,
  disabled: Boolean,
  members: Array,
  hasAttachments: Boolean,
  label: { type: String, default: 'Write a reply' },
  sendLabel: { type: String, default: 'Send' }
});
const emit = defineEmits(['update:modelValue', 'submit', 'files']);
const field = ref(null),
  mention = ref(null),
  activeMention = ref(0);
const root = ref(null),
  width = ref(400),
  fieldHeight = ref(UI.metrics.minimum);
let observer;
const geometry = computed(() =>
  UI.layout(
    width.value,
    fieldHeight.value,
    props.label === 'Note text',
    mobile.value
  )
);
const bounds = (rect) => ({
  position: 'absolute',
  left: rect.x + 'px',
  top: rect.y + 'px',
  width: rect.width + 'px',
  height: rect.height + 'px'
});
function measure() {
  if (root.value?.clientWidth > 0) width.value = root.value.clientWidth;
  if (field.value && !props.modelValue) {
    fieldHeight.value = UI.metrics.minimum;
    return;
  }
  if (field.value) {
    const old = field.value.style.height;
    field.value.style.height = '0px';
    const content =
      field.value.scrollHeight -
      UI.metrics.paddingTop -
      UI.metrics.paddingBottom;
    field.value.style.height = old;
    fieldHeight.value = UI.field(content);
  }
}
onMounted(() => {
  observer = observeFrameSizes(measure);
  observer.observe(root.value);
  measure();
});
onBeforeUnmount(() => observer?.disconnect());
watch(
  () => props.modelValue,
  () => nextTick(measure)
);
const matches = computed(() =>
  props.members.filter((row) =>
    (row.login + ' ' + (row.displayName || ''))
      .toLowerCase()
      .includes((mention.value || '').toLowerCase())
  )
);
const mentionId = useId();
const optionId = (login) => mentionId + '-mention-' + encodeURIComponent(login);
function findMention() {
  if (props.sending || props.disabled) {
    mention.value = null;
    return;
  }
  mention.value = State.mentionQuery(
    field.value.value,
    field.value.selectionStart
  );
  activeMention.value = 0;
}
function input() {
  emit('update:modelValue', field.value.value);
  findMention();
}
async function insert(value, replace = 0) {
  if (props.disabled || props.sending) return;
  const start = field.value.selectionStart,
    end = field.value.selectionEnd;
  emit(
    'update:modelValue',
    State.insertion(props.modelValue, start, end, value, replace).text
  );
  mention.value = null;
  await nextTick();
  field.value.focus();
  field.value.setSelectionRange(
    start - replace + value.length,
    start - replace + value.length
  );
}
function key(event) {
  const command = State.composerKey(
    {
      key: event.key,
      keyCode: event.keyCode,
      composing: event.isComposing,
      control: event.ctrlKey,
      meta: event.metaKey,
      repeat: event.repeat,
      disabled: props.disabled,
      sending: props.sending
    },
    mobile.value,
    mention.value !== null,
    !!matches.value.length
  );
  if (command === 'pass') return;
  event.preventDefault();
  if (command === 'dismiss') {
    event.stopPropagation();
    mention.value = null;
  } else if (command === 'mention')
    insert(
      '@' + matches.value[activeMention.value].login + ' ',
      mention.value.length + 1
    );
  else if (command === 'next' || command === 'previous') {
    activeMention.value =
      (activeMention.value +
        (command === 'next' ? 1 : matches.value.length - 1)) %
      matches.value.length;
    nextTick(() =>
      document
        .getElementById(optionId(matches.value[activeMention.value]?.login))
        ?.scrollIntoView({ block: 'nearest' })
    );
  } else if (command === 'newline') insert('\n');
  else if (command === 'send') emit('submit');
}
watch(
  () => props.modelValue,
  (value) => {
    if (value !== field.value?.value) mention.value = null;
  }
);
watch(
  () => props.sending || props.disabled,
  (value) => {
    if (value) mention.value = null;
  }
);
defineExpose({
  focus() {
    field.value?.focus();
  }
});
</script>
<template>
  <div
    ref="root"
    class="message-composer"
    :style="{ height: geometry.height + 'px' }"
  >
    <div class="message-composer-field" :style="bounds(geometry.field)">
      <textarea
        ref="field"
        :value="modelValue"
        :disabled="disabled"
        :readonly="sending"
        :aria-label="t(label)"
        :placeholder="
          t(
            label === 'Note text'
              ? mobile
                ? 'Write a note'
                : 'Write a note · Enter to send · Ctrl+Enter for a new line'
              : mobile
                ? 'Write a reply'
                : 'Write a reply · Enter to send · Ctrl+Enter for a new line'
          )
        "
        :aria-controls="
          mention !== null && matches.length
            ? mentionId + '-members'
            : undefined
        "
        :aria-activedescendant="
          mention !== null && matches.length
            ? optionId(matches[activeMention]?.login)
            : undefined
        "
        aria-autocomplete="list"
        rows="1"
        @input="input"
        @click="findMention"
        @keydown="key"
        @paste="
          (event) => {
            if (event.clipboardData.files.length && !sending && !disabled) {
              event.preventDefault();
              emit('files', event.clipboardData.files);
            }
          }
        "
      ></textarea
      ><EmojiPicker
        data-frame="messageComposerEmojiButton"
        v-if="!sending"
        :style="{ '--composer-emoji-extent': UI.metrics.emoji + 'px' }"
        label="Insert emoji"
        :disabled="disabled || sending"
        @selected="insert"
      />
    </div>
    <div
      v-if="mention !== null && matches.length"
      :id="mentionId + '-members'"
      class="message-mentions"
      role="listbox"
      :aria-label="t('Mention a member')"
      :style="{ width: Math.min(296, geometry.field.width) + 'px' }"
    >
      <FrameView
        v-for="(member, index) in matches"
        :key="member.login"
        :scene="
          Panels.mention(
            {
              ...member,
              selected: index === activeMention,
              elementId: optionId(member.login)
            },
            Math.max(0, Math.min(296, geometry.field.width) - 30)
          )
        "
        @event="(event) => insert('@' + event.login + ' ', mention.length + 1)"
      />
    </div>
    <AppButton
      data-frame="messageComposerSendButton"
      class="message-send"
      :style="bounds(geometry.send)"
      :icon-only="geometry.compact"
      :label="sending ? 'Sending' : sendLabel"
      icon="send"
      highlighted
      :disabled="disabled || sending || (!modelValue.trim() && !hasAttachments)"
      @click="emit('submit')"
    />
  </div>
</template>

<style>
.message-composer {
  position: relative;
  display: block;
  flex: 1;
  min-width: 0;
}
.message-composer-field {
  position: relative;
  min-width: 0;
  border-radius: var(--surface-radius);
  background: var(--surface-high);
  padding: 2px !important;
  border: 0 !important;
  outline: none;
  box-shadow: inset 0 0 0 1px var(--outline);
}
.message-composer-field:focus-within {
  box-shadow: inset 0 0 0 2px var(--primary);
}
.message-composer textarea {
  resize: none;
  width: 100%;
  min-width: 0;
  border: 0;
  background: transparent;
  color: var(--on-surface);
  font-family: var(--font-family);
  border-radius: inherit;
  height: 100%;
  min-height: 0;
  padding: 8px 42px 8px 12px;
  line-height: 18px;
  font-size: 14px;
  field-sizing: fixed;
  outline: 0;
}
.message-composer > .message-send {
  min-width: 0 !important;
}
.message-composer > .message-mentions {
  padding: 8px;
  border: 0;
  height: 226px;
  max-height: 226px;
  overflow: auto;
  scrollbar-gutter: stable;
}
.message-mentions > .frame-view {
  height: 46px;
  flex: none;
}
</style>
