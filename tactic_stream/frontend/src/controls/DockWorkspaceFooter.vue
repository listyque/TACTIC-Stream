<script setup>
import { computed } from 'vue';
import { appearance } from '../appearance.js';
import { metrics } from '../../../src/tactic_stream/shared_ui/core/foundation.mjs';
import { footer } from '../../../src/tactic_stream/shared_ui/shell/dock.surface.mjs';
const props = defineProps({
  nativeDialog: Boolean,
  topLeft: Boolean,
  topRight: Boolean,
  bottomLeft: { type: Boolean, default: undefined },
  bottomRight: { type: Boolean, default: undefined },
  divider: { type: Boolean, default: true }
});
const surface = computed(() =>
  footer(metrics(appearance.theme).surfaceRadius, props.nativeDialog, props)
);
const style = computed(() => ({
  height: surface.value.height + 'px',
  borderTopWidth: surface.value.divider + 'px',
  borderTopLeftRadius: surface.value.topLeft + 'px',
  borderTopRightRadius: surface.value.topRight + 'px',
  borderBottomLeftRadius: surface.value.bottomLeft + 'px',
  borderBottomRightRadius: surface.value.bottomRight + 'px'
}));
</script>
<template>
  <footer class="dock-workspace-footer" :style="style"><slot /></footer>
</template>
<style>
.dock-workspace-footer {
  flex-shrink: 0;
  background: var(--surface-container);
  border-top: 1px solid var(--outline-variant);
}
</style>
