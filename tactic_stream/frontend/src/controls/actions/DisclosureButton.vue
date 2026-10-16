<script setup>
import AppButton from '../AppButton.vue';
import BusyIndicator from '../BusyIndicator.vue';
import { nextTick, ref, watch } from 'vue';
const props = defineProps({
  identity: { type: String, required: true },
  expanded: Boolean,
  loading: Boolean,
  hasChildren: Boolean,
  label: String
});
const emit = defineEmits(['click']);
const requested = ref(false);
watch(
  () => props.identity,
  () => {
    requested.value = false;
  }
);
watch(
  () => props.loading,
  (value) => {
    if (!value) requested.value = false;
  }
);
function activate(event) {
  if (!props.hasChildren || props.loading) return;
  requested.value = true;
  emit('click', event);
  nextTick(() => {
    if (!props.loading) requested.value = false;
  });
}
</script>

<template>
  <AppButton
    class="disclosure-button"
    icon-only
    :icon="!hasChildren || (loading && requested) ? undefined : 'chevron-right'"
    :label="label || (expanded ? 'Collapse item' : 'Expand item')"
    :disabled="!hasChildren || loading"
    :aria-expanded="expanded"
    :aria-busy="loading"
    :aria-hidden="!hasChildren || undefined"
    @click="activate"
  >
    <BusyIndicator v-if="loading && requested" running />
  </AppButton>
</template>

<style>
.disclosure-button.app-button.icon-button {
  --motion-click-extended: 0ms;
  background: transparent;
  color: var(--muted);
}
.disclosure-button.app-button.icon-button:hover {
  background: transparent;
}
.disclosure-button.app-button.icon-button > .app-icon {
  width: 15px;
  height: 15px;
  font-size: 15px;
  transform: rotate(0);
  transition: transform var(--motion-click) ease-out;
}
.disclosure-button[aria-expanded='true'] > .app-icon {
  transform: rotate(90deg);
}
.disclosure-button .busy-indicator {
  width: 22px;
  height: 22px;
}
</style>
