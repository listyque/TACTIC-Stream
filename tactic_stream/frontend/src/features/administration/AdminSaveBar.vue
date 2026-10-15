<script setup>
// AdministrationView.qml / AdminSaveBar.qml: shared order, status and geometry.
import AppButton from '../../controls/AppButton.vue';
import AppIcon from '../../controls/AppIcon.vue';
import BusyIndicator from '../../controls/BusyIndicator.vue';
import { t } from '../../i18n.js';
defineProps({
  busy: Boolean,
  dirty: Boolean,
  canWrite: Boolean,
  saveDisabled: Boolean,
  discardDisabled: Boolean,
  saveLabel: { type: String, default: 'Save to server' }
});
defineEmits(['save', 'discard']);
</script>
<template>
  <div class="administration-save-bar">
    <div class="administration-leading-actions"><slot /></div>
    <span class="administration-save-status muted">
      <template v-if="busy || dirty || !canWrite"
        ><BusyIndicator v-if="busy" /><AppIcon
          v-else
          :name="dirty ? 'edit' : 'lock'"
        />{{
          t(
            busy
              ? 'Working on the server…'
              : dirty
                ? 'Unsaved changes'
                : 'Read-only'
          )
        }}</template
      >
    </span>
    <AppButton
      label="Discard"
      icon="reset"
      :disabled="discardDisabled"
      @click="$emit('discard')"
    />
    <AppButton
      label="Save to server"
      :aria-label="t(saveLabel)"
      icon="save"
      highlighted
      :disabled="saveDisabled"
      @click="$emit('save')"
    />
    <slot name="trailing" />
  </div>
</template>
<style>
.administration-save-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 620px;
  max-width: 100%;
  height: var(--control-height);
}
.administration-leading-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.administration-save-status {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  font-size: var(--text-label);
  overflow: hidden;
  text-overflow: ellipsis;
}
.administration-save-status .busy-indicator {
  width: 22px;
  height: 22px;
}
.administration-shell .administration-save-bar .app-button:not(.icon-button) {
  background: var(--surface-high);
  border: 0;
  border-radius: var(--button-radius);
}
.administration-shell
  .administration-save-bar
  .app-button.primary:not(:disabled) {
  background: var(--primary);
}
@media (max-width: 1079px) {
  .administration-save-bar {
    width: auto;
  }
  .administration-save-status {
    display: none;
  }
}
</style>
