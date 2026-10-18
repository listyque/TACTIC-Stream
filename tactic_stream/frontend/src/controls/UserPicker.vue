<script setup>
// Handler UserPicker.qml (EPL-1.0): current user stays visible but cannot be selected.
import { computed, ref, onMounted, onBeforeUnmount } from 'vue';
import FrameView from '../frame/FrameView.vue';
import { appearance } from '../appearance.js';
import { observeFrameSizes } from '../frame/resize.js';
import * as UI from '../../../src/tactic_stream/shared_ui/controls/forms/people.ui.mjs';
import AppSearchField from './AppSearchField.vue';
import UserGroupSection from './UserGroupSection.vue';
import { matchesUser } from './userSearch.js';
import { t } from '../i18n.js';
const props = defineProps({
  users: Array,
  currentLogin: String,
  disabled: Boolean,
  includeCurrent: Boolean
});
const selected = defineModel({ type: Array, default: () => [] });
const query = ref(''),
  root = ref(null),
  width = ref(400);
let observer;
onMounted(() => {
  observer = observeFrameSizes((entries) => {
    if (entries[0].contentRect.width > 0)
      width.value = entries[0].contentRect.width;
  });
  observer.observe(root.value);
});
onBeforeUnmount(() => observer?.disconnect());
const rows = computed(() =>
  (props.users || []).filter(
    (user) => !user.retired && matchesUser(user, query.value)
  )
);
const groups = computed(() =>
  [...new Set(rows.value.map((user) => user.primaryGroup || 'Ungrouped'))].map(
    (title) => ({
      title,
      users: rows.value.filter(
        (user) => (user.primaryGroup || 'Ungrouped') === title
      )
    })
  )
);
function toggle(login) {
  if (props.disabled || (!props.includeCurrent && login === props.currentLogin))
    return;
  selected.value = selected.value.includes(login)
    ? selected.value.filter((value) => value !== login)
    : [...selected.value, login];
}
</script>
<template>
  <div ref="root" class="user-picker">
    <AppSearchField
      v-model="query"
      label="Search users"
      :placeholder="t('Search users')"
      :disabled="disabled"
    />
    <div class="user-picker-list">
      <template v-for="group in groups" :key="group.title">
        <UserGroupSection :title="group.title" />
        <FrameView
          v-for="user in group.users"
          :key="user.login"
          class="user-picker-surface"
          :style="{ height: UI.metrics.row + 'px' }"
          :scene="
            UI.row(
              {
                ...user,
                picker: true,
                selected: selected.includes(user.login),
                selectable:
                  !disabled && (includeCurrent || user.login !== currentLogin),
                currentUnavailable:
                  !includeCurrent && user.login === currentLogin
              },
              Math.max(0, width - UI.metrics.scrollbar),
              appearance.language
            )
          "
          @event="(event) => toggle(event.login)"
        />
      </template>
    </div>
  </div>
</template>
<style>
.user-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  flex: 1;
}
.user-picker > .app-search-field {
  flex: none;
  height: var(--control-height);
  min-height: var(--control-height);
  padding-inline: 11px;
  gap: 8px;
}
.user-picker > .app-search-field input {
  min-width: 0;
  height: 100%;
  min-height: 0;
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
}
.user-picker > .app-search-field > .app-icon {
  width: 18px;
  height: 18px;
  font-size: 18px;
}
.user-picker-list {
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  min-height: 0;
  flex: 1;
  padding-right: 2px;
}
.user-picker-surface {
  position: relative;
  flex: none;
  min-width: 0;
}
</style>
