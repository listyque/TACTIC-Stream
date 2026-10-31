<script setup>
import { controls } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
// Handler UserComboBox.qml: one assignee, searchable/grouped choices, no API.
import { computed, nextTick, ref } from 'vue';
import AppMenu from './AppMenu.vue';
import AppButton from './AppButton.vue';
import AppSearchField from './AppSearchField.vue';
import AppIcon from './AppIcon.vue';
import ItemPreview from './ItemPreview.vue';
import UserGroupSection from './UserGroupSection.vue';
import { matchesUser } from './userSearch.js';
import { t } from '../i18n.js';
const props = defineProps({
  value: String,
  placeholder: String,
  emptyLabel: { type: String, default: 'Not assigned' },
  options: { type: Array, default: () => [] },
  disabled: Boolean,
  actionField: { type: Boolean, default: true },
  label: { type: String, default: 'Assigned to' }
});
const emit = defineEmits(['change']);
const menu = ref(null),
  query = ref(''),
  popupWidth = ref(controls.userPicker.popupWidth),
  expanded = ref(false);
const users = computed(() => [
  {
    value: '',
    login: '',
    displayName: t(props.emptyLabel),
    primaryGroup: 'Ungrouped'
  },
  ...props.options
    .filter((option) => option.value)
    .map((option) => ({
      ...option,
      login: option.value,
      displayName: option.label || option.displayName || option.value,
      initials:
        option.initials ||
        (option.label || option.displayName || option.value)
          .trim()
          .split(/\s+/)
          .map((word) => word[0])
          .filter(Boolean)
          .filter(
            (_, index, parts) => index === 0 || index === parts.length - 1
          )
          .join('')
          .toUpperCase(),
      primaryGroup: option.primaryGroup || 'Ungrouped'
    }))
]);
const current = computed(
  () =>
    users.value.find((user) => user.login === props.value) || {
      login: props.value,
      displayName: props.value
    }
);
const groups = computed(() => {
  const rows = users.value
    .filter((user) => matchesUser(user, query.value))
    .sort(
      (a, b) =>
        (a.login ? 1 : 0) - (b.login ? 1 : 0) ||
        a.primaryGroup
          .toLowerCase()
          .localeCompare(b.primaryGroup.toLowerCase()) ||
        a.displayName.toLowerCase().localeCompare(b.displayName.toLowerCase())
    );
  return [...new Set(rows.map((user) => user.primaryGroup))].map((title) => ({
    title,
    users: rows.filter((user) => user.primaryGroup === title)
  }));
});
function choose(user) {
  if (props.disabled) return;
  emit('change', user.value);
  menu.value.close(true);
}
function prepare() {
  query.value = '';
  const font = getComputedStyle(menu.value.$el),
    context = document.createElement('canvas').getContext('2d');
  context.font = `600 ${font.fontSize} ${font.fontFamily}`;
  popupWidth.value = Math.max(
    250,
    menu.value.$el.getBoundingClientRect().width,
    ...users.value.map(
      (user) => context.measureText(user.displayName).width + 116
    )
  );
}
function opened(event) {
  if (event.target !== menu.value?.$el) return;
  expanded.value = event.newState === 'open';
  if (!expanded.value) return;
  nextTick(() => {
    if (menu.value?.open) menu.value.$el.querySelector('input')?.focus();
  });
}
function searchKey(event) {
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    (
      menu.value.$el.querySelector('.user-combo-option[aria-checked="true"]') ||
      menu.value.$el.querySelector('.user-combo-option')
    )?.focus();
  }
}
function optionKey(event) {
  if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
  event.preventDefault();
  event.stopPropagation();
  const rows = [...menu.value.$el.querySelectorAll('.user-combo-option')],
    index = rows.indexOf(event.currentTarget);
  rows[
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? rows.length - 1
        : (index + (event.key === 'ArrowUp' ? -1 : 1) + rows.length) %
          rows.length
  ]?.focus();
}
</script>
<template>
  <AppMenu
    ref="menu"
    class="user-combo-box"
    :class="{ 'user-combo-field': !actionField, disabled }"
    :label="label"
    :disabled="disabled"
    overlay
    align-start
    :width="popupWidth"
    :close-on-select="false"
    @before-open="prepare"
    @toggle="opened"
  >
    <template #trigger
      ><ItemPreview
        :source="current.avatarUrl"
        :fallback-text="current.initials"
        fallback-icon="user"
        :accent="current.avatarColor"
        :preview-size="22"
        round
        outlined /><span class="user-combo-label">{{
        placeholder || current.displayName
      }}</span
      ><AppIcon
        v-if="!actionField"
        class="user-combo-indicator"
        :name="expanded ? 'MDI_CHEVRON_UP' : 'MDI_CHEVRON_DOWN'"
    /></template>
    <AppSearchField
      v-model="query"
      label="Search users"
      :placeholder="t('Search users')"
      :disabled="disabled"
      @keydown="searchKey"
      @search="groups[0]?.users[0] && choose(groups[0].users[0])"
    />
    <div class="user-combo-list">
      <template v-for="group in groups" :key="group.title"
        ><UserGroupSection :title="group.title" compact />
        <AppButton
          v-for="user in group.users"
          :key="user.login"
          class="user-combo-option"
          :label="user.displayName"
          role="radio"
          :aria-checked="value === user.login"
          :disabled="disabled"
          @keydown="optionKey"
          @click="choose(user)"
        >
          <ItemPreview
            :source="user.avatarUrl"
            :fallback-text="user.initials"
            fallback-icon="user"
            :accent="user.avatarColor"
            :preview-size="32"
            round
            outlined
          /><span class="user-combo-copy"
            ><strong>{{ user.displayName }}</strong
            ><small v-if="user.login">{{ user.login }}</small></span
          ><AppIcon
            v-if="value === user.login"
            class="user-combo-check"
            name="MDI_CHECK_CIRCLE"
          />
        </AppButton>
      </template>
    </div>
  </AppMenu>
</template>
<style>
.user-combo-box.workspace-menu {
  position: relative;
  width: auto;
  min-width: 0;
  height: 28px;
  font-size: var(--control-text-size);
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
}
.workspace-menu.user-combo-box > summary.icon-button {
  display: flex;
  justify-content: flex-start;
  gap: 7px;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: 0 11px;
  border: 0;
  border-radius: var(--item-radius);
  background: var(--surface);
  color: var(--on-surface);
}
.workspace-menu.user-combo-box > summary:hover {
  background: var(--surface-high);
}
.user-combo-box > summary > .user-combo-label {
  flex: 1;
  min-width: 0;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 400;
  font-size: var(--control-text-size);
}
.user-combo-box > summary > .image-picker-preview {
  width: 22px;
  height: 22px;
  min-width: 22px;
  min-height: 22px;
  flex: 0 0 22px;
}
.user-combo-box.disabled > summary.icon-button {
  color: var(--disabled);
  cursor: default;
}
.user-combo-box.disabled > summary > .image-picker-preview {
  opacity: 0.58;
}
.user-combo-box.user-combo-field {
  height: var(--control-height);
}
.workspace-menu.user-combo-field > summary.icon-button {
  padding-inline: 10px 8px;
  border: 1px solid var(--outline-variant);
  border-radius: var(--field-radius);
}
.user-combo-indicator.app-icon {
  flex: none;
  --icon-size: 17px;
  width: 17px;
  height: 17px;
  color: var(--muted);
}
.user-combo-box > .account-panel {
  height: var(--user-picker-popup-height);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.user-combo-box > .account-panel > .app-search-field {
  flex: none;
  height: 36px;
  min-height: 36px;
  padding-inline: 12px;
  gap: 8px;
}
.user-combo-box .app-search-field > input {
  min-width: 0;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border: 0;
  background: transparent;
}
.user-combo-box .app-search-field > .app-icon {
  width: 16px;
  height: 16px;
  font-size: 16px;
}
.user-combo-list {
  overflow: auto;
  overscroll-behavior: contain;
  flex: 1;
  min-height: 0;
}
.user-combo-box .user-combo-list > .user-combo-option.app-button {
  display: flex;
  gap: 9px;
  align-items: center;
  width: 100%;
  height: var(--user-picker-row-height);
  min-height: var(--user-picker-row-height);
  padding: 4px 9px 4px 8px;
  background: transparent;
  border: 0;
  text-align: left;
}
.user-combo-box .user-combo-list > .user-combo-option[aria-checked='true'],
.user-combo-box .user-combo-list > .user-combo-option:focus-visible {
  background: var(--hover);
}
.user-combo-option > .image-picker-preview {
  width: var(--user-picker-avatar-size);
  height: var(--user-picker-avatar-size);
  flex: 0 0 var(--user-picker-avatar-size);
}
.user-combo-option > .user-combo-copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}
.user-combo-option strong,
.user-combo-option small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.user-combo-option strong {
  font-size: var(--control-text-size);
  font-weight: 600;
}
.user-combo-option small {
  font-size: var(--text-caption);
  color: var(--muted);
}
.user-combo-option > .user-combo-check.app-icon {
  flex: none;
  width: 16px;
  height: 16px;
  font-size: 16px;
  color: var(--primary);
}
</style>
