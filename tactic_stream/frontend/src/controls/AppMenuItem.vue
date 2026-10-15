<script setup>
import { t } from '../i18n.js'
import AppButton from './AppButton.vue'
import AppIcon from './AppIcon.vue'

defineOptions({ inheritAttrs: false })
defineProps({ label: String, icon: String, checked: { type: Boolean, default: undefined },
  disabled: Boolean, disabledReason: String, translate: { type: Boolean, default: true }, secondaryLabel: String,
  secondaryIcon: { type: String, default: 'close' } })
const emit = defineEmits(['click', 'secondary'])
</script>

<template>
  <div class="app-menu-item">
    <AppButton v-bind="$attrs" data-menu-primary :icon="icon" :label="label"
      :aria-label="translate ? t(label) : label" :title="disabled && disabledReason ? t(disabledReason) : translate ? t(label) : label" :aria-description="disabled && disabledReason ? t(disabledReason) : undefined"
      :role="checked === undefined ? 'menuitem' : 'menuitemradio'" :aria-checked="checked" :disabled="disabled" @click="emit('click', $event)">
      <span class="app-menu-item-label">{{ translate ? t(label) : label }}</span>
      <AppIcon v-if="checked" name="check-circle" class="menu-check" />
    </AppButton>
    <AppButton v-if="secondaryLabel" data-menu-secondary icon-only :icon="secondaryIcon" :label="secondaryLabel"
      role="menuitem" :disabled="disabled" @click="emit('secondary', $event)" />
  </div>
</template>

<style>
.app-menu-item { display:flex; min-width:0; height:var(--compact-control-height); border-radius:var(--item-radius); }
.app-menu-item > [data-menu-primary] { flex:1; min-width:0; padding-inline:10px 8px; }
.app-menu-item-label { flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.app-menu-item > [data-menu-secondary] { flex:0 0 30px; width:30px; min-width:30px; height:100%; min-height:0; padding:0; justify-content:center; }
.account-panel .app-menu-item .app-icon { width:16px; height:16px; font-size:16px; }
.account-panel .app-menu-item .menu-check { flex:0 0 18px; width:18px; height:18px; font-size:18px; }
.account-panel .app-menu-item > [data-menu-secondary] .app-icon { width:15px; height:15px; font-size:15px; }
.app-menu-item:has(> [data-menu-primary]:hover:not(:disabled)), .app-menu-item:focus-within { background:var(--hover); }
</style>
