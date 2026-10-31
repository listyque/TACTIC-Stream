<script setup>
import { ref, computed, watch, nextTick } from 'vue';
import AppMenu from './AppMenu.vue';
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import FrameView from '../frame/FrameView.vue';
import { appearance } from '../appearance.js';
import { mobile } from '../mobile.js';
import {
  virtualRange,
  revealListOffset
} from '../../../src/tactic_stream/shared_ui/core/frame.mjs';
import * as UI from '../../../src/tactic_stream/shared_ui/controls/forms/emoji.ui.mjs';
import { t } from '../i18n.js';
const props = defineProps({
  label: { type: String, default: 'Choose emoji' },
  disabled: Boolean,
  textTrigger: Boolean,
  externalTrigger: Boolean
});
const emit = defineEmits(['selected']);
const menu = ref(null),
  anchor = ref(null),
  query = ref(''),
  category = ref('Smileys & Emotion'),
  entries = ref([]),
  error = ref('');

const shown = computed(() =>
  entries.value.filter((row) =>
    query.value
      ? row.name.includes(query.value.toLowerCase()) ||
        row.value === query.value
      : row.category === category.value
  )
);
const grid = ref(null),
  scroll = ref(0),
  screenWidth = ref(innerWidth),
  screenHeight = ref(innerHeight);
const bounds = computed(() => UI.popup(screenWidth.value, screenHeight.value));
const geometry = computed(() =>
  UI.layout(bounds.value.width - 20, bounds.value.height - 20, mobile.value)
);
const rowCount = computed(() =>
  Math.ceil(shown.value.length / geometry.value.columns)
);
const range = computed(() =>
  virtualRange(
    rowCount.value,
    Math.max(1, geometry.value.cell),
    geometry.value.grid.height,
    scroll.value,
    2
  )
);
const cells = computed(() =>
  shown.value
    .slice(
      range.value.first * geometry.value.columns,
      range.value.last * geometry.value.columns
    )
    .map((row, index) => ({
      ...row,
      index: index + range.value.first * geometry.value.columns
    }))
);
watch([query, category], () => {
  scroll.value = 0;
  if (grid.value) grid.value.scrollTop = 0;
});
function heading(event) {
  if (event.type === 'query') query.value = event.value;
  else {
    category.value = event.value;
    query.value = '';
  }
}
async function move(event) {
  const index = Number(
    event.target.closest('[data-emoji-index]')?.dataset.emojiIndex
  );
  if (!Number.isInteger(index)) return;
  const columns = geometry.value.columns,
    delta = {
      ArrowLeft: -1,
      ArrowRight: 1,
      ArrowUp: -columns,
      ArrowDown: columns
    }[event.key];
  if (delta === undefined) return;
  event.preventDefault();
  const next = (index + delta + shown.value.length) % shown.value.length;
  const top = revealListOffset(
    grid.value.scrollTop,
    Math.floor(next / columns),
    geometry.value.grid.height,
    rowCount.value,
    geometry.value.cell,
    0
  );
  scroll.value = top;
  grid.value.scrollTop = top;
  await nextTick();
  grid.value.querySelector('[data-emoji-index="' + next + '"]')?.focus();
}
async function load() {
  screenWidth.value = innerWidth;
  screenHeight.value = innerHeight;
  if (!menu.value?.open || entries.value.length) return;
  try {
    entries.value = (await import('../assets/emoji.json')).default;
    error.value = '';
  } catch {
    error.value = 'Unable to load emoji. Try again.';
  }
}
function select(value) {
  emit('selected', value);
  menu.value.close(true);
}
defineExpose({
  openFor(source) {
    anchor.value = source;
    if (menu.value.open) menu.value.close(true);
    else menu.value.openAt({ target: source });
  }
});
</script>
<template>
  <AppMenu
    ref="menu"
    :external-trigger="externalTrigger"
    :anchor="anchor"
    class="emoji-picker"
    :class="{ 'menu-entry': textTrigger }"
    :label="label"
    icon="emoji"
    :disabled="disabled"
    :width="bounds.width"
    overlay
    :close-on-select="false"
    @toggle="load"
  >
    <template v-if="textTrigger" #trigger
      ><AppIcon name="emoji" /><span>{{ t(label) }}</span></template
    >
    <FrameView
      class="emoji-picker-header"
      :scene="
        UI.heading({ query, category }, bounds.width - 20, appearance.language)
      "
      @event="heading"
    />
    <p v-if="error" role="alert">
      {{ t(error) }} <AppButton label="Retry" @click="load" />
    </p>
    <div
      ref="grid"
      class="emoji-grid"
      :style="{ height: geometry.grid.height + 'px' }"
      @scroll.passive="scroll = $event.target.scrollTop"
      @keydown="move"
    >
      <div
        :style="{
          height: rowCount * geometry.cell + 'px',
          position: 'relative'
        }"
      >
        <AppButton
          v-for="row in cells"
          :key="row.value"
          :data-emoji-index="row.index"
          :aria-label="row.name"
          :title="row.name"
          :style="{
            position: 'absolute',
            left: (row.index % geometry.columns) * geometry.cell + 'px',
            top:
              Math.floor(row.index / geometry.columns) * geometry.cell + 'px',
            width: geometry.cell + 'px',
            height: geometry.cell + 'px',
            minHeight: geometry.cell + 'px',
            fontSize: UI.cell(row, geometry.cell, mobile).fontSize + 'px'
          }"
          @click="select(row.value)"
          >{{ row.value }}</AppButton
        >
      </div>
    </div>
    <p v-if="entries.length && !shown.length">{{ t('No matching emoji') }}</p>
  </AppMenu>
</template>
<style>
@font-face {
  font-family: 'Noto Color Emoji';
  src: url('/assets/NotoColorEmoji.ttf') format('truetype');
  font-display: swap;
}
.emoji-picker .account-panel {
  padding: 10px;
  gap: 8px;
}
.emoji-picker-header {
  height: 76px;
  flex: none;
}
.emoji-picker.menu-entry > summary {
  width: 100%;
  min-width: 0;
  height: var(--control-height);
  justify-content: flex-start;
  gap: 8px;
  padding: 0 12px;
  font-size: var(--text-body);
}
.emoji-grid {
  display: block;
  overflow: auto;
  scrollbar-gutter: stable;
  flex: none;
  min-width: 0;
}
.emoji-picker .emoji-grid .app-button {
  min-width: 0;
  padding: 0;
  justify-content: center;
  font-family: 'Noto Color Emoji', 'Segoe UI Emoji', sans-serif;
  line-height: 1;
  border: 0;
  border-radius: 9px;
  background: transparent;
}
.emoji-picker .emoji-grid .app-button:hover {
  background: var(--surface-high);
}
</style>
