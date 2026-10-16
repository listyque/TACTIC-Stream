<script setup>
import { computed } from 'vue';
import { fraction } from '../../../src/tactic_stream/shared_ui/controls/display/progress.mjs';
import { t } from '../i18n.js';
const props = defineProps({
  label: String,
  value: Number,
  min: { type: Number, default: 0 },
  max: { type: Number, default: 1 }
});
const position = computed(() => fraction(props.value, props.min, props.max));
</script>

<template>
  <span
    class="app-progress"
    :class="{ determinate: position !== null }"
    role="progressbar"
    :aria-label="t(label)"
    :aria-valuemin="position !== null ? min : undefined"
    :aria-valuemax="position !== null ? max : undefined"
    :aria-valuenow="
      position !== null ? Math.max(min, Math.min(max, value)) : undefined
    "
    :style="{ '--progress-value': position }"
  ></span>
</template>

<style scoped>
/* Qt Material: 1240ms OutCubic slide, 520ms pause; x=v*w, width=v*(w-x). */
@property --progress-slide {
  syntax: '<number>';
  inherits: false;
  initial-value: 0;
}
.app-progress {
  display: block;
  position: relative;
  width: 100%;
  height: var(--feedback-progress-height);
  overflow: hidden;
  background: color-mix(in srgb, var(--primary) 25%, transparent);
}
.app-progress::before,
.app-progress::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: calc(var(--progress-slide) * 100%);
  width: calc(var(--progress-slide) * (1 - var(--progress-slide)) * 100%);
  background: var(--primary);
  animation: progress-first 1760ms cubic-bezier(0.333333, 1, 0.666667, 1)
    infinite;
}
.app-progress::after {
  animation-name: progress-second;
}
@keyframes progress-first {
  0% {
    --progress-slide: 0;
  }
  70.454545%,
  100% {
    --progress-slide: 1;
  }
}
@keyframes progress-second {
  0%,
  29.545455% {
    --progress-slide: 0;
  }
  100% {
    --progress-slide: 1;
  }
}
.app-progress.determinate::before {
  animation: none;
  left: 0;
  width: calc(var(--progress-value) * 100%);
}
.app-progress.determinate::after {
  display: none;
}
/* ponytail: CSS replaces Qt scene-graph rasterization; validate other browser engines before claiming parity. */
@media (prefers-reduced-motion: reduce) {
  .app-progress::before {
    animation: none;
    --progress-slide: 0.5;
  }
  .app-progress::after {
    display: none;
  }
}
</style>
