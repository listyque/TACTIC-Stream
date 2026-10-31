<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue';
import AppDialog from '../../controls/AppDialog.vue';
import AppButton from '../../controls/AppButton.vue';
import { t } from '../../i18n.js';
const props = defineProps({ frameNode: { type: Object, required: true } });
const emit = defineEmits(['event']);
const dialog = ref(null);
let outcome = '';
watch(
  () => props.frameNode.open,
  async (opened) => {
    await nextTick();
    if (opened) {
      outcome = '';
      dialog.value?.show();
    } else if (dialog.value?.open) dialog.value.close();
  },
  { immediate: true }
);
function finish(value) {
  outcome = value;
  dialog.value.close();
}
function closed() {
  if (props.frameNode.open)
    emit('event', { ...props.frameNode.action, value: outcome || 'cancel' });
}
onBeforeUnmount(() => {
  if (dialog.value?.open) dialog.value.close();
});
</script>
<template>
  <div>
    <AppDialog
      ref="dialog"
      :title="frameNode.text"
      :translate-title="false"
      :style="{ width: (frameNode.popupWidth || 440) + 'px' }"
      @closed="closed"
    >
      <p :role="frameNode.error ? 'alert' : undefined">
        {{ frameNode.message }}
      </p>
      <footer class="window-actions">
        <AppButton
          :label="frameNode.cancelText || t('Cancel')"
          @click="finish('cancel')"
        />
        <AppButton
          :label="frameNode.acceptText || t('Apply')"
          highlighted
          :disabled="!frameNode.enabled"
          @click="finish('accept')"
        />
      </footer>
    </AppDialog>
  </div>
</template>
