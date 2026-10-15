<script setup>
// Main.qml notificationActivityButton: 36/220 extent, 32 surface, 760 breakpoint.
import AppButton from '../../controls/AppButton.vue'
import AppIcon from '../../controls/AppIcon.vue'
import BusyIndicator from '../../controls/BusyIndicator.vue'
import { t } from '../../i18n.js'

defineProps({ busy: Boolean, message: String, compact: Boolean })
defineEmits(['open'])
</script>

<template>
  <div class="system-activity-control" :class="{ busy, 'in-menu': compact }" @click.self="$emit('open')">
    <AppButton class="system-activity-trigger" :icon-only="!compact" label="System activity"
      :title="t(busy ? message : 'System activity')" :aria-description="busy ? t(message) : undefined" @click="$emit('open')">
      <AppIcon class="activity-icon" name="system-activity" />
      <span class="activity-progress"><BusyIndicator :running="busy" /><span class="progress-label">{{ t(message) }}</span></span>
      <span v-if="compact" class="activity-menu-label">{{ t('System activity') }}<small v-if="busy">{{ t(message) }}</small></span>
    </AppButton>
  </div>
</template>

<style scoped>
.system-activity-control { width: 36px; height: 36px; flex-shrink: 0; overflow: hidden; cursor: pointer; transition: width var(--motion-medium) var(--motion-easing-out-cubic); }
.system-activity-control.busy { width: 220px; }
.system-activity-control .system-activity-trigger { position: relative; display: flex; width: calc(100% - 2px); min-width: 0; height: 32px; min-height: 0; margin: 2px 1px; padding: 0; border: 1px solid transparent; border-radius: 16px; background: transparent; transition: background var(--motion-medium) var(--motion-easing-out-cubic), border-color var(--motion-medium) var(--motion-easing-out-cubic); }
.busy .system-activity-trigger { background: var(--surface); border-color: var(--outline-variant); }
.system-activity-trigger::before { content: ''; position: absolute; inset: 0; border-radius: inherit; background: var(--on-surface); opacity: 0; pointer-events: none; transition: opacity var(--motion-hover) var(--motion-easing-out-cubic); }
.system-activity-control:hover .system-activity-trigger::before, .system-activity-trigger:focus-visible::before { opacity: .08; }
.system-activity-control:active .system-activity-trigger::before { opacity: .12; transition-duration: var(--motion-click); }
.system-activity-control .activity-icon { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); width: 20px; height: 20px; font-size: 20px; opacity: 1; }
.activity-progress { position: absolute; inset: 0 11px 0 9px; display: flex; align-items: center; gap: 7px; opacity: 0; pointer-events: none; }
.progress-label { min-width: 0; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; font: 500 var(--text-body) var(--font-family); }
.activity-icon, .activity-progress { transition: opacity var(--motion-medium) var(--motion-easing-out-cubic); }
.busy .activity-icon { opacity: 0; }
.busy .activity-progress { opacity: 1; }
@media (max-width: 759px) {
  .system-activity-control.busy { width: 36px; }
  .activity-progress { left: 6px; right: 6px; }
  .progress-label { display: none; }
}
.system-activity-control.in-menu { width: 100%; height: auto; }
.in-menu .system-activity-trigger { width: 100%; height: auto; min-height: 32px; margin: 0; padding: 7px 10px; justify-content: start; border-radius: var(--button-radius); background: transparent; border: 0; }
.system-activity-control.in-menu .activity-icon { position: static; transform: none; flex-shrink: 0; }
.in-menu .activity-progress { inset: auto; left: 10px; }
.in-menu .progress-label { display: none; }
.activity-menu-label { min-width: 0; text-align: start; }
.activity-menu-label small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
</style>
