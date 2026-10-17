<script setup>
import { computed, ref, watch, nextTick, onBeforeUnmount, useId } from 'vue';
import AppTextField from '../../controls/AppTextField.vue';
import AppButton from '../../controls/AppButton.vue';
import AppMenu from '../../controls/AppMenu.vue';
import FrameView from '../../frame/FrameView.vue';
import { qtLabelTextWidth } from '../../controls/typography/textMetrics.js';
import { fontFamily } from '../../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import * as UI from '../../../../src/tactic_stream/shared_ui/features/search/conditions.ui.mjs';
const props = defineProps({
  frameNode: Object,
  suggestions: Object,
  active: { type: Boolean, default: true }
});
const emit = defineEmits(['event']);
const suggestionId = useId();
const field = ref(null),
  popup = ref(null),
  width = ref(240),
  opened = ref(false),
  selected = ref(-1),
  anchor = ref(null);
const records = computed(() =>
  props.suggestions?.index === props.frameNode.index
    ? props.suggestions.records || []
    : []
);
const scenes = computed(() =>
  records.value.map((record) =>
    UI.suggestion(
      {
        ...record,
        titleWidth: qtLabelTextWidth(
          record.title,
          '600 13px "' + fontFamily + '"'
        ),
        keywordWidth: qtLabelTextWidth(
          '#' + record.keyword,
          '600 12px "' + fontFamily + '"'
        )
      },
      width.value
    )
  )
);
function send(type, extra = {}) {
  emit('event', {
    type,
    index: props.frameNode.index,
    column: props.frameNode.column,
    ...extra
  });
}
function edit(value) {
  send('condition', { field: 'value', value });
  send('suggest', { value });
}
function close() {
  opened.value = false;
  popup.value?.close();
  send('dismiss');
}
function accept(index) {
  const record = records.value[index];
  if (!record) return;
  send('condition', {
    field: 'value',
    value: record.values?.[props.frameNode.column] ?? record.title
  });
  close();
  field.value.focus();
}
watch(records, async () => {
  selected.value = -1;
  if (!records.value.length || document.activeElement !== field.value?.$el) {
    popup.value?.close();
    return;
  }
  anchor.value = field.value.$el;
  const bounds = anchor.value.getBoundingClientRect();
  width.value = Math.max(190, bounds.width);
  await nextTick();
  popup.value.openAt({
    clientX: bounds.left,
    clientY: bounds.bottom + 4,
    target: anchor.value
  });
});
watch(
  () => props.active,
  (active) => {
    if (!active) close();
  }
);
function key(event) {
  if (event.isComposing) return;
  if (['ArrowDown', 'ArrowUp'].includes(event.key) && records.value.length) {
    event.preventDefault();
    selected.value =
      (selected.value +
        (event.key === 'ArrowDown' ? 1 : -1) +
        records.value.length) %
      records.value.length;
    nextTick(() =>
      popup.value.$el
        .querySelectorAll('.condition-suggestion-row')
        [selected.value]?.scrollIntoView({ block: 'nearest' })
    );
  } else if (event.key === 'Enter') {
    event.preventDefault();
    if (opened.value && selected.value >= 0) accept(selected.value);
    else {
      close();
      send('apply');
    }
  } else if (event.key === 'Escape' && opened.value) {
    event.preventDefault();
    event.stopPropagation();
    close();
  }
}
let blurTimer;
function blur() {
  clearTimeout(blurTimer);
  blurTimer = setTimeout(() => {
    if (!popup.value?.$el.matches(':hover')) close();
  }, 140);
}
onBeforeUnmount(() => clearTimeout(blurTimer));
</script>
<template>
  <div class="condition-value">
    <AppTextField
      ref="field"
      :model-value="frameNode.text"
      :label="frameNode.label"
      :placeholder="frameNode.placeholder"
      :disabled="!frameNode.enabled"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="opened"
      :aria-controls="suggestionId"
      :aria-activedescendant="
        opened && selected >= 0 ? suggestionId + '-' + selected : undefined
      "
      @update:model-value="edit"
      @keydown="key"
      @blur="blur"
    />
    <AppMenu
      ref="popup"
      external-trigger
      frame-composition
      overlay
      :focus-on-open="false"
      :anchor="anchor"
      :width="width + 8"
      :close-on-select="false"
      label="Search suggestions"
      @toggle="opened = $event.currentTarget.open"
    >
      <div :id="suggestionId" role="listbox" :aria-label="frameNode.label">
        <AppButton
          v-for="(record, index) in records"
          :key="index"
          :id="suggestionId + '-' + index"
          role="option"
          :aria-selected="index === selected"
          tabindex="-1"
          class="condition-suggestion-row"
          :class="{ selected: index === selected }"
          :label="record.title"
          :translate-label="false"
          @pointerdown.prevent
          @click="accept(index)"
          ><FrameView :scene="scenes[index]" :interactive="false"
        /></AppButton>
      </div>
    </AppMenu>
  </div>
</template>
<style>
.condition-value > .app-text-field {
  width: 100%;
  height: 100%;
}
.condition-suggestion-row.app-button {
  position: relative;
  height: 34px;
  min-height: 34px;
  width: 100%;
  padding: 0;
  border-radius: var(--item-radius);
  background: transparent;
}
.condition-suggestion-row.app-button > .frame-view {
  width: 100%;
  height: 34px;
}
.condition-suggestion-row.selected,
.condition-suggestion-row:hover {
  background: var(--secondary-container);
}
</style>
