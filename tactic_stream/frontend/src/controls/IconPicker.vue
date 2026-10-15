<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import AppButton from './AppButton.vue';
import AppIcon from './AppIcon.vue';
import AppSelect from './AppSelect.vue';
import AppTextField from './AppTextField.vue';
import AppMenu from './AppMenu.vue';
import { t } from '../i18n.js';
import { appearance, iconSets } from '../appearance.js';
import { iconMaps } from '../icons.js';
import { controls } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { virtualRange } from '../../../src/tactic_stream/shared_ui/core/frame.mjs';

const props = defineProps({
  modelValue: String,
  disabled: Boolean,
  iconOnly: Boolean,
  tacticCompatibleOnly: Boolean
});
const emit = defineEmits(['update:modelValue']);
const menu = ref(null),
  search = ref(''),
  family = ref('material-design'),
  grid = ref(null);
const viewport = ref({ width: 480, height: 280, offset: 0 });
let observer;
const sets = computed(() =>
  iconSets.filter(
    (option) =>
      iconMaps[option.value] &&
      (!props.tacticCompatibleOnly || option.value === 'fontawesome-solid')
  )
);
const names = computed(() =>
  Object.keys(iconMaps[family.value])
    .sort()
    .filter((name) => name.includes(search.value.toLowerCase().trim()))
);
const columns = computed(() =>
  Math.max(1, Math.floor((viewport.value.width - 4) / 96))
);
const rowCount = computed(() => Math.ceil(names.value.length / columns.value));
const visible = computed(() => {
  const range = virtualRange(
    rowCount.value,
    76,
    viewport.value.height,
    viewport.value.offset,
    1
  );
  return names.value
    .slice(range.first * columns.value, range.last * columns.value)
    .map((name, index) => ({
      name,
      index: range.first * columns.value + index
    }));
});
const value = (name) =>
  props.tacticCompatibleOnly ? name : family.value + ':' + name;
function select(name) {
  emit('update:modelValue', value(name));
  menu.value.close(true);
}
function prepare() {
  const explicit = props.modelValue?.split(':')[0],
    legacy = /^(FA|FAS|FAR|MDI)_/i.exec(props.modelValue || '');
  const preferred = iconMaps[explicit]
    ? explicit
    : legacy
      ? {
          FA: 'fontawesome-solid',
          FAS: 'fontawesome-solid',
          FAR: 'fontawesome-outline',
          MDI: 'material-design'
        }[legacy[1].toUpperCase()]
      : appearance.iconSet;
  family.value = props.tacticCompatibleOnly
    ? 'fontawesome-solid'
    : iconMaps[preferred]
      ? preferred
      : 'material-design';
  search.value = '';
}
function opened(event) {
  if (event.target !== menu.value?.$el) return;
  if (event.newState !== 'open') {
    observer?.disconnect();
    return;
  }
  nextTick(() => {
    if (!menu.value?.open || !grid.value) return;
    menu.value?.$el.querySelector('.app-text-field')?.focus();
    observer?.disconnect();
    observer = new ResizeObserver((entries) => {
      const box = entries[0].contentRect;
      viewport.value = {
        width: box.width,
        height: box.height,
        offset: grid.value.scrollTop
      };
    });
    observer.observe(grid.value);
  });
}
watch([search, family], () => {
  if (grid.value) grid.value.scrollTop = 0;
  viewport.value = { ...viewport.value, offset: 0 };
});
function move(event, index) {
  const step = {
    ArrowLeft: -1,
    ArrowRight: 1,
    ArrowUp: -columns.value,
    ArrowDown: columns.value
  }[event.key];
  if (step === undefined && event.key !== 'Home' && event.key !== 'End') return;
  event.preventDefault();
  event.stopPropagation();
  const target =
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? names.value.length - 1
        : Math.max(0, Math.min(names.value.length - 1, index + step));
  const top = Math.floor(target / columns.value) * 76;
  if (top < grid.value.scrollTop) grid.value.scrollTop = top;
  else if (top + 76 > grid.value.scrollTop + grid.value.clientHeight)
    grid.value.scrollTop = top + 76 - grid.value.clientHeight;
  viewport.value = { ...viewport.value, offset: grid.value.scrollTop };
  nextTick(() =>
    grid.value.querySelector(`[data-icon-index="${target}"]`)?.focus()
  );
}
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <AppMenu
    ref="menu"
    compact-trigger
    class="icon-picker-control"
    label="Choose icon"
    :disabled="disabled"
    :show-label="!iconOnly"
    overlay
    :width="controls.iconPicker.popupWidth"
    :max-height="controls.iconPicker.popupHeight"
    :close-on-select="false"
    @before-open="prepare"
    @toggle="opened"
  >
    <template #trigger
      ><AppIcon :name="modelValue || 'image'" /><span v-if="!iconOnly">{{
        t('Choose icon')
      }}</span></template
    >
    <div class="icon-picker">
      <header>
        <AppIcon name="shapes" /><strong>{{ t('Icon library') }}</strong
        ><small>{{ names.length }}</small
        ><AppSelect
          v-if="sets.length > 1"
          v-model="family"
          :options="sets"
          label="Icon set"
        />
      </header>
      <AppTextField
        v-model="search"
        label="Search icons"
        placeholder="Search icons"
        @keydown.down.prevent="grid.querySelector('button')?.focus()"
      />
      <div
        ref="grid"
        class="icon-library"
        role="group"
        :aria-label="t('Icon library')"
        @scroll="viewport = { ...viewport, offset: $event.target.scrollTop }"
      >
        <div :style="{ height: rowCount * 76 + 'px' }">
          <AppButton
            v-for="item in visible"
            :key="item.name"
            :data-icon-index="item.index"
            :aria-label="item.name"
            :aria-pressed="
              modelValue === value(item.name) || modelValue === item.name
            "
            :style="{
              left: (item.index % columns) * (100 / columns) + '%',
              top: Math.floor(item.index / columns) * 76 + 'px',
              width: 100 / columns + '%'
            }"
            @keydown="move($event, item.index)"
            @click="select(item.name)"
            ><AppIcon :name="family + ':' + item.name" /><small>{{
              item.name
            }}</small></AppButton
          >
        </div>
      </div>
    </div>
  </AppMenu>
</template>

<style>
.icon-picker-control > .account-panel {
  height: var(--icon-picker-popup-height);
  padding: 9px;
  overflow: hidden;
}
.icon-picker-control .icon-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  height: 100%;
  min-height: 0;
}
.icon-picker > header {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: none;
  height: var(--control-height);
}
.icon-picker > header strong {
  flex: 1;
  min-width: 0;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.icon-picker > header small {
  color: var(--muted);
}
.icon-picker > header .app-select {
  width: 190px;
  min-width: 100px;
}
.icon-picker > .app-text-field {
  flex: none;
  width: 100%;
}
.icon-picker .icon-library {
  display: block;
  flex: 1;
  min-height: 0;
  max-height: none;
  overflow: auto;
  margin: 0;
  padding: 5px;
  scrollbar-gutter: stable;
  border: 1px solid var(--outline-variant);
  border-radius: var(--surface-radius);
  background: var(--surface-low);
}
.icon-library > div {
  position: relative;
  margin-right: 4px;
}
.icon-picker .icon-library .app-button {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 3px;
  height: 76px;
  min-height: 0;
  padding: 9px;
  border: 0;
  background: transparent;
  box-shadow: none;
  border-radius: var(--item-radius);
  font-size: var(--text-caption);
}
.icon-picker .icon-library .app-button > .app-icon {
  width: 28px;
  height: 28px;
  font-size: 28px;
}
.icon-picker .icon-library .app-button > small {
  display: block;
  flex: none;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--muted);
}
.icon-picker .icon-library .app-button:hover,
.icon-picker .icon-library .app-button:focus-visible {
  background: var(--hover);
}
.icon-picker .icon-library .app-button[aria-pressed='true'] {
  background: var(--selected);
  color: var(--on-selected);
}
.icon-picker .icon-library .app-button[aria-pressed='true'] > small {
  color: var(--on-selected);
}
.frame-icon-choice > .icon-picker-control,
.frame-icon-choice > .icon-picker-control > summary {
  width: 100%;
  height: 100%;
}
.frame-icon-choice > .icon-picker-control > summary {
  display: flex;
  justify-content: center;
  padding: 0;
  background: transparent;
}
.frame-icon-choice > .icon-picker-control > summary > .app-icon {
  width: 17px;
  height: 17px;
  font-size: 17px;
}
@media (max-width: 420px) {
  .icon-picker > header .app-select {
    width: 136px;
  }
  .icon-picker > header strong {
    font-size: 11px;
  }
}

.icon-picker > header > .app-icon {
  width: 19px;
  height: 19px;
  font-size: 19px;
}
.icon-picker > header > small {
  font-size: 12px;
}
.icon-picker .icon-library .app-button > small {
  font-size: 11px;
  line-height: 15px;
}
.icon-picker .icon-library .app-button {
  isolation: isolate;
}
.icon-picker .icon-library .app-button::before {
  content: '';
  position: absolute;
  z-index: -1;
  inset: 3px;
  border-radius: var(--item-radius);
}
.icon-picker .icon-library .app-button:hover,
.icon-picker .icon-library .app-button:focus-visible,
.icon-picker .icon-library .app-button[aria-pressed='true'] {
  background: transparent;
}
.icon-picker .icon-library .app-button:hover::before,
.icon-picker .icon-library .app-button:focus-visible::before {
  background: var(--hover);
}
.icon-picker .icon-library .app-button[aria-pressed='true']::before {
  background: var(--selected);
  border: 1px solid var(--primary);
}
</style>
