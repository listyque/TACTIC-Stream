<script setup>
import { t } from '../i18n.js';
import { ref, onMounted, onBeforeUnmount } from 'vue';

defineProps({
  controlId: String,
  title: String,
  description: String,
  path: String,
  showDivider: { type: Boolean, default: true }
});
const root = ref(null),
  accessory = ref(null),
  stacked = ref(false);
let observer;
onMounted(() => {
  observer = new ResizeObserver(() => {
    stacked.value =
      root.value.clientWidth - 28 - accessory.value.scrollWidth < 210;
  });
  observer.observe(root.value);
  observer.observe(accessory.value);
});
onBeforeUnmount(() => observer?.disconnect());
</script>

<template>
  <div
    ref="root"
    class="settings-row configuration-setting"
    :class="{ stacked, 'no-divider': !showDivider }"
  >
    <div class="setting-description">
      <label :for="controlId"
        ><strong>{{ t(title) }}</strong></label
      ><code v-if="path">{{ path }}</code>
      <p v-if="description" :id="controlId + '-help'" class="muted">
        {{ t(description) }}
      </p>
      <slot name="description" />
    </div>
    <div ref="accessory" class="setting-control"><slot /></div>
  </div>
</template>
<style>
.settings-row.configuration-setting {
  position: relative;
  grid-template-columns: minmax(0, 1fr) max-content;
  column-gap: 20px;
  row-gap: 8px;
  padding: 10px 4px;
}
.settings-row.configuration-setting::after {
  content: '';
  position: absolute;
  left: 4px;
  right: 4px;
  bottom: 0;
  height: 1px;
  background: var(--outline-variant);
}
.settings-row.configuration-setting.no-divider::after {
  display: none;
}
.settings-row.configuration-setting .setting-description {
  gap: 3px;
}
.settings-row.configuration-setting .setting-description strong {
  font-size: var(--font-body-size);
  line-height: var(--font-body-line-height);
}
.settings-row.configuration-setting .setting-description p {
  margin: 0;
  font-size: var(--font-caption-size);
  line-height: var(--font-caption-line-height);
}
.settings-row.configuration-setting .setting-control {
  width: max-content;
  max-width: 100%;
  justify-self: end;
}
.settings-row.configuration-setting.stacked {
  grid-template-columns: minmax(0, 1fr);
}
</style>
