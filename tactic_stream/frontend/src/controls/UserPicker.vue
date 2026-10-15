<script setup>
// Handler UserPicker.qml (EPL-1.0): current user stays visible but cannot be selected.
import { computed, ref } from 'vue'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'
import AppSearchField from './AppSearchField.vue'
import ItemPreview from './ItemPreview.vue'
import ItemSurface from './ItemSurface.vue'
import UserGroupSection from './UserGroupSection.vue'
import { matchesUser } from './userSearch.js'
import { t } from '../i18n.js'
const props = defineProps({ users: Array, currentLogin: String, disabled: Boolean })
const selected = defineModel({ type: Array, default: () => [] })
const query = ref('')
const rows = computed(() => (props.users || []).filter(user => !user.retired && matchesUser(user, query.value)))
const groups = computed(() => [...new Set(rows.value.map(user => user.primaryGroup || 'Ungrouped'))].map(title => ({ title, users: rows.value.filter(user => (user.primaryGroup || 'Ungrouped') === title) })))
function toggle(login) {
  if (props.disabled || login === props.currentLogin) return
  selected.value = selected.value.includes(login) ? selected.value.filter(value => value !== login) : [...selected.value, login]
}
</script>
<template>
  <div class="user-picker">
    <AppSearchField v-model="query" label="Search users" :placeholder="t('Search users')" :disabled="disabled" />
    <div class="user-picker-list">
      <template v-for="group in groups" :key="group.title">
        <UserGroupSection :title="group.title" />
        <ItemSurface v-for="user in group.users" :key="user.login" class="user-picker-surface" :selected="selected.includes(user.login)" :corner-radius="12" :inset="0">
          <AppButton class="user-picker-row" role="checkbox" :aria-checked="selected.includes(user.login)" :aria-label="user.displayName || user.login" :disabled="disabled || user.login === currentLogin" @click="toggle(user.login)">
            <ItemPreview :source="user.avatarUrl" :fallback-text="user.initials" :accent="user.avatarColor" :preview-size="36" round outlined />
            <span class="user-picker-label"><strong>{{ user.displayName || user.login }}</strong><small>{{ user.login }}<template v-if="user.groups?.length"> · {{ user.groups.join(', ') }}</template></small></span>
            <AppIcon v-if="selected.includes(user.login)" class="user-picker-check" name="MDI_CHECK_CIRCLE" />
            <span v-else-if="user.login === currentLogin" class="user-picker-current"><AppIcon name="MDI_LOCK" />{{ t('Current user') }}</span>
          </AppButton>
        </ItemSurface>
      </template>
    </div>
  </div>
</template>
<style>
.user-picker { display:flex; flex-direction:column; gap:8px; min-height:0; flex:1; }
.user-picker > .app-search-field { flex:none; height:36px; min-height:36px; padding-inline:12px; gap:8px; }
.user-picker > .app-search-field input { min-width:0; height:34px; min-height:34px; font-size:var(--text-body); }
.user-picker > .app-search-field > .app-icon { width:16px; height:16px; font-size:16px; }
.user-picker-list { overflow:auto; overscroll-behavior:contain; scrollbar-gutter:stable; min-height:0; flex:1; padding-right:2px; }
.user-picker-surface > .item-surface-rail, .user-picker-surface::after { display:none; }
.user-picker .user-picker-row.app-button { display:flex; gap:8px; align-items:center; width:100%; height:54px; min-height:54px; padding:8px; border:0; border-radius:12px; background:transparent; color:var(--on-surface); text-align:left; }
.user-picker .user-picker-row.app-button:hover:not(:disabled) { background:transparent; }
.user-picker-row.app-button:disabled { opacity:1; }
.user-picker-row:disabled .image-picker-preview { opacity:.58; }
.user-picker-row:disabled .user-picker-label strong { color:var(--muted); }
.user-picker-surface.selected .outlined-preview { border-color:var(--on-selected); }
.user-picker-surface.selected .user-picker-label > * { color:var(--on-selected); }
.user-picker-row .image-picker-preview { width:36px; height:36px; flex:0 0 36px; }
.user-picker-label { flex:1; min-width:0; display:flex; flex-direction:column; gap:1px; }
.user-picker-label strong { font-size:var(--text-body); font-weight:600; }
.user-picker-label small { font-size:var(--text-caption); color:var(--muted); }
.user-picker-label > * { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.user-picker .user-picker-check.app-icon { font-size:18px; color:var(--on-selected); }
.user-picker-current { display:flex; align-items:center; gap:5px; height:24px; padding:0 8px; border-radius:12px; color:var(--muted); background:var(--hover); font-size:var(--text-caption); white-space:nowrap; }
.user-picker .user-picker-current .app-icon { font-size:12px; }
</style>
