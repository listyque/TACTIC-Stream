<script setup>
defineProps({ running: Boolean });
</script>

<template>
  <span class="busy-indicator" :class="{ running }" aria-hidden="true"></span>
</template>

<style scoped>
/* Qt Material qquickmaterialbusyindicator.cpp: 10–300° span, 700ms phases, 720°/4200ms. */
@property --busy-sweep {
  syntax: '<angle>';
  inherits: false;
  initial-value: 10deg;
}
@property --busy-tail {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
@property --busy-base {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
.busy-indicator {
  display: inline-block;
  width: var(--feedback-busy-extent);
  height: var(--feedback-busy-extent);
  flex: 0 0 auto;
  position: relative;
  visibility: hidden;
}
.busy-indicator::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: conic-gradient(
    from calc(90deg + var(--busy-base) + var(--busy-tail)),
    var(--primary) var(--busy-sweep),
    transparent 0
  );
  mask: radial-gradient(
    closest-side,
    transparent calc(100% - 2px),
    black calc(100% - 2px)
  );
}
.busy-indicator.running {
  visibility: visible;
}
.busy-indicator.running::before {
  animation:
    busy-indicator-turn 4200ms linear infinite,
    busy-indicator-span 1400ms infinite,
    busy-indicator-tail 1400ms infinite,
    busy-indicator-base 50400ms steps(36, end) infinite;
}
@keyframes busy-indicator-turn {
  to {
    transform: rotate(720deg);
  }
}
@keyframes busy-indicator-span {
  0% {
    --busy-sweep: 10deg;
    animation-timing-function: cubic-bezier(0.333333, 0.666667, 0.666667, 1);
  }
  50% {
    --busy-sweep: 300deg;
    animation-timing-function: cubic-bezier(0.333333, 0, 0.666667, 0.333333);
  }
  100% {
    --busy-sweep: 10deg;
  }
}
@keyframes busy-indicator-tail {
  0%,
  50% {
    --busy-tail: 0deg;
    animation-timing-function: cubic-bezier(0.333333, 0, 0.666667, 0.333333);
  }
  100% {
    --busy-tail: 290deg;
  }
}
/* 36 phases return the cumulative 290° start shift to the same angle. */
@keyframes busy-indicator-base {
  to {
    --busy-base: 10440deg;
  }
}
@media (prefers-reduced-motion: reduce) {
  .busy-indicator.running::before {
    animation: none;
  }
}
</style>
